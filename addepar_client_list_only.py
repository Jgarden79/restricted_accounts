"""
Lightweight Addepar Client List Retrieval Module

This minimal module ONLY retrieves the client list from Addepar API.
All other functionality has been removed for simplicity and speed.
"""

import time
import requests
import json
import pandas as pd
import io
import base64
import os
from datetime import datetime
from pathlib import Path
import threading


class AddepalClientRetriever:
    """Simple class to retrieve only the client list from Addepar

    This class includes a minimal in-memory cache to avoid posting the same
    job repeatedly within the same Python process. If get_client_list is
    called multiple times with the same end_date within a 24-hour window,
    it will return the cached DataFrame instead of posting a new job.
    """
    
    # Module/process-level lightweight cache to prevent duplicate postings
    _cache = {
        'end_date': None,
        'timestamp': None,
        'df': None,
    }
    # Simple in-flight marker to avoid concurrent duplicate posts
    _inflight = {
        'end_date': None,
        'since': None,
    }
    # Class-level lock to prevent concurrent duplicate postings
    _lock = threading.Lock()

    def __init__(self, auth_string=None, firm_id="222"):
        """
        Initialize the client retriever
        
        Args:
            auth_string: Your Addepar API credentials (username:password)
                        If None, will try to get from ADDEPAR_AUTH env variable
            firm_id: Your Addepar firm ID (default: "222")
        """
        self.base_url = "https://lido.addepar.com/api/v1/jobs"
        self.firm_id = firm_id
        self.client_list_view_id = 420336  # Default client list view ID
        
        # Set up authentication
        if auth_string:
            self.auth = base64.b64encode(bytes(auth_string, 'utf-8'))
        else:
            # Try to get from environment variable
            auth_env = os.getenv('ADDEPAR_AUTH')
            if auth_env:
                self.auth = base64.b64encode(bytes(auth_env, 'utf-8'))
            else:
                raise ValueError("No authentication provided. Pass auth_string or set ADDEPAR_AUTH environment variable")
    
    def _post_job(self, payload):
        """Post a job to Addepar API with robust JSON handling and retries"""
        headers = {
            "Accept": "application/vnd.api+json",
            "Addepar-Firm": self.firm_id,
            "Content-Type": "application/vnd.api+json",
            "Authorization": f"Basic {self.auth.decode('utf-8')}"
        }

        last_err = None
        for attempt in range(3):
            response = requests.post(self.base_url, data=json.dumps(payload), headers=headers)
            try:
                response.raise_for_status()
            except Exception as e:
                last_err = e
                # Retry on transient server errors
                if response is not None and 500 <= response.status_code < 600 and attempt < 2:
                    time.sleep(1 + attempt)
                    continue
                raise

            content = response.content or b""
            content_len = len(content)
            if content_len == 0:
                last_err = ValueError("Empty response body when posting job")
                # Retry if attempts remain
                if attempt < 2:
                    time.sleep(1 + attempt)
                    continue
                raise last_err

            # Try robust JSON parsing
            json_dict = None
            try:
                # First, tolerant decode for BOM
                decoded = content.decode('utf-8-sig').strip()
                if not decoded:
                    raise ValueError("Empty decoded JSON body")
                json_dict = json.loads(decoded)
            except Exception:
                # Fallback to requests' JSON parser
                try:
                    json_dict = response.json()
                except Exception as parse_err:
                    # Include a small snippet for diagnostics
                    snippet = decoded[:200] if 'decoded' in locals() else content[:200]
                    last_err = ValueError(f"Failed to parse JSON from job post response: {parse_err}; snippet={snippet}")
                    if attempt < 2:
                        time.sleep(1 + attempt)
                        continue
                    raise last_err

            try:
                job_id = json_dict['data']['id']
            except Exception as key_err:
                # Not the expected JSON shape; retry if possible
                last_err = ValueError(f"Unexpected job post JSON structure: {key_err}; keys={list(json_dict.keys()) if isinstance(json_dict, dict) else type(json_dict)}")
                if attempt < 2:
                    time.sleep(1 + attempt)
                    continue
                raise last_err

            print(f"Job posted successfully. Job ID: {job_id}")
            return job_id

        # Should not reach here
        assert False, f"_post_job failed after retries: {last_err}"
    
    def _check_status(self, job_id):
        """Check the status of a posted job with robust handling and retries"""
        headers = {
            "Accept": "application/vnd.api+json",
            "Addepar-Firm": self.firm_id,
            "Authorization": f"Basic {self.auth.decode('utf-8')}"
        }

        url = f"{self.base_url}/{job_id}"

        last_err = None
        for attempt in range(5):
            response = requests.get(url, headers=headers, allow_redirects=False)

            # 303 usually means job completed with download available
            if response.status_code == 303:
                return 1.0

            if response.status_code == 204:
                # No content yet; treat as 0% and retry
                if attempt < 4:
                    time.sleep(1 + 0.5 * attempt)
                    continue
                return 0.0

            if response.status_code >= 500 and attempt < 4:
                time.sleep(1 + 0.5 * attempt)
                continue

            try:
                response.raise_for_status()
            except Exception as e:
                last_err = e
                if attempt < 4:
                    time.sleep(1 + 0.5 * attempt)
                    continue
                raise

            content = response.content or b""
            if len(content) == 0:
                # Empty body; retry
                if attempt < 4:
                    time.sleep(1 + 0.5 * attempt)
                    continue
                raise ValueError("Empty response body when checking job status")

            try:
                decoded = content.decode('utf-8-sig').strip()
                if not decoded:
                    raise ValueError("Empty decoded status body")
                json_dict = json.loads(decoded)
            except Exception:
                try:
                    json_dict = response.json()
                except Exception as parse_err:
                    last_err = ValueError(f"Failed to parse JSON from job status: {parse_err}")
                    if attempt < 4:
                        time.sleep(1 + 0.5 * attempt)
                        continue
                    raise last_err

            try:
                percent_complete = json_dict['data']['attributes']['percent_complete']
                return percent_complete
            except Exception as key_err:
                last_err = ValueError(f"Unexpected status JSON structure: {key_err}; keys={list(json_dict.keys()) if isinstance(json_dict, dict) else type(json_dict)}")
                if attempt < 4:
                    time.sleep(1 + 0.5 * attempt)
                    continue
                raise last_err

        # Should not reach here
        assert False, f"_check_status failed after retries: {last_err}"
    
    def _download_results(self, job_id):
        """Download the results of a completed job with robust CSV handling"""
        headers = {
            "Accept": "application/vnd.api+json",
            "Addepar-Firm": self.firm_id,
            "Authorization": f"Basic {self.auth.decode('utf-8')}"
        }

        url = f"{self.base_url}/{job_id}/download"
        response = requests.get(url, headers=headers)
        response.raise_for_status()

        content = response.content or b""
        if len(content) == 0:
            raise ValueError("Empty CSV download content from Addepar")

        try:
            # Handle potential BOM in CSV
            df = pd.read_csv(io.BytesIO(content), encoding='utf-8-sig')
        except Exception as e:
            snippet = content[:200]
            raise ValueError(f"Failed to parse CSV download: {e}; snippet={snippet}")
        return df
    
    def get_client_list(self, end_date=None, save_to_csv=False, csv_path=None):
        """
        Retrieve the client list from Addepar
        
        Args:
            end_date: The end date for the client list (format: YYYY-MM-DD)
                     If None, uses today's date
            save_to_csv: Whether to save the result to a CSV file
            csv_path: Path to save the CSV file (default: 'client_list.csv')
        
        Returns:
            pd.DataFrame: DataFrame containing the client list
        """
        # Use today's date if not provided
        if end_date is None:
            end_date = datetime.today().strftime("%Y-%m-%d")
        
        # Check process-local cache to avoid duplicate postings
        try:
            cached_end = self.__class__._cache['end_date']
            cached_time = self.__class__._cache['timestamp']
            cached_df = self.__class__._cache['df']
        except Exception:
            cached_end = cached_time = cached_df = None

        if cached_df is not None and cached_end == end_date and cached_time is not None:
            age_hours = (datetime.now() - cached_time).total_seconds() / 3600.0
            if age_hours < 24:
                print(f"Using in-memory cached Addepar data for {end_date} ({age_hours:.1f}h old)")
                # Optionally re-save CSV to requested path without re-fetching
                if save_to_csv and cached_df is not None:
                    csv_file = csv_path or 'client_list.csv'
                    cached_df.to_csv(csv_file, index=False)
                    print(f"Saved cached data to {csv_file}")
                return cached_df
        
        # Lock to prevent concurrent duplicate postings
        with self.__class__._lock:
            # Re-check cache after acquiring the lock
            try:
                cached_end = self.__class__._cache['end_date']
                cached_time = self.__class__._cache['timestamp']
                cached_df = self.__class__._cache['df']
            except Exception:
                cached_end = cached_time = cached_df = None

            if cached_df is not None and cached_end == end_date and cached_time is not None:
                age_hours = (datetime.now() - cached_time).total_seconds() / 3600.0
                if age_hours < 24:
                    print(f"Using in-memory cached Addepar data for {end_date} ({age_hours:.1f}h old) [post-lock]")
                    if save_to_csv and cached_df is not None:
                        csv_file = csv_path or 'client_list.csv'
                        cached_df.to_csv(csv_file, index=False)
                        print(f"Saved cached data to {csv_file}")
                    return cached_df

            print(f"Retrieving client list as of {end_date}...")
            
            # Prepare the job payload
            payload = {
                "data": {
                    "attributes": {
                        "parameters": {
                            "end_date": end_date, 
                            "view_id": self.client_list_view_id,
                            "portfolio_type": "FIRM", 
                            "start_date": "2016-05-29",  # Default start date
                            "output_type": "CSV", 
                            "portfolio_id": 1
                        },
                        "job_type": "portfolio_view_results"
                    }, 
                    "type": "jobs"
                }
            }
            
            # Post the job
            job_id = self._post_job(payload)
            
            # Wait for job completion
            print("Waiting for job to complete...")
            while True:
                progress = self._check_status(job_id)
                print(f"Progress: {progress:.1%}", end='\r')
                
                if progress >= 1.0:
                    print("\nJob completed!")
                    break
                
                time.sleep(5)  # Check every 5 seconds
            
            # Download results
            print("Downloading results...")
            client_df = self._download_results(job_id)
            
            print(f"Successfully retrieved {len(client_df)} clients")
            
            # Save to CSV if requested
            if save_to_csv:
                csv_file = csv_path or 'client_list.csv'
                client_df.to_csv(csv_file, index=False)
                print(f"Saved to {csv_file}")
            
            # Update process-local cache
            self.__class__._cache = {
                'end_date': end_date,
                'timestamp': datetime.now(),
                'df': client_df,
            }
            
            return client_df


# Convenience function for quick usage
def get_addepar_clients(auth_string=None, end_date=None, save_csv=False):
    """
    Quick function to get Addepar client list
    
    Args:
        auth_string: Your Addepar API credentials (username:password)
        end_date: The end date for the client list (YYYY-MM-DD format)
        save_csv: Whether to save the result to 'client_list.csv'
    
    Returns:
        pd.DataFrame: Client list DataFrame
    
    Example:
        # Using environment variable for auth
        clients = get_addepar_clients(end_date="2024-12-31", save_csv=True)
        
        # Using direct auth string
        clients = get_addepar_clients(auth_string="username:password")
    """
    retriever = AddepalClientRetriever(auth_string)
    return retriever.get_client_list(end_date, save_csv)


# Example usage
if __name__ == "__main__":
    # Example 1: Using environment variable for authentication
    # Set ADDEPAR_AUTH environment variable to "username:password"
    try:
        client_retriever = AddepalClientRetriever()
        clients = client_retriever.get_client_list(save_to_csv=True)
        print(f"\nFirst 5 clients:")
        print(clients.head())
    except ValueError as e:
        print(f"Error: {e}")
        print("Please set ADDEPAR_AUTH environment variable or pass auth_string")
    
    # Example 2: Using direct authentication
    # auth = "your_username:your_password"
    # client_retriever = AddepalClientRetriever(auth_string=auth)
    # clients = client_retriever.get_client_list(end_date="2024-12-31")
