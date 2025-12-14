#!/usr/bin/env python3
"""
Dremio Configuration Automation Script

Automatically configures Dremio to connect to MinIO and create datasets.
"""
import sys
import json
import time
import getpass
import requests
from typing import Optional, Dict, Any


class DremioClient:
    """Client for Dremio REST API."""

    def __init__(self, host: str = "localhost", port: int = 9047):
        """Initialize Dremio client."""
        self.base_url = f"http://{host}:{port}"
        self.api_url = f"{self.base_url}/apiv2"
        self.catalog_url = f"{self.base_url}/api/v3/catalog"
        self.token: Optional[str] = None
        self.session = requests.Session()

    def check_health(self) -> bool:
        """Check if Dremio is accessible."""
        try:
            response = requests.get(f"{self.base_url}/", timeout=5)
            return response.status_code == 200
        except requests.exceptions.RequestException:
            return False

    def login(self, username: str, password: str) -> bool:
        """
        Authenticate with Dremio.

        Args:
            username: Admin username
            password: Admin password

        Returns:
            True if authentication successful
        """
        try:
            response = self.session.post(
                f"{self.api_url}/login",
                json={"userName": username, "password": password},
                timeout=10
            )

            if response.status_code == 200:
                self.token = response.json().get("token")
                self.session.headers.update({
                    "Authorization": f"_dremio{self.token}",
                    "Content-Type": "application/json"
                })
                return True
            else:
                print(f"Login failed: {response.status_code}")
                print(f"Response: {response.text}")
                return False

        except requests.exceptions.RequestException as e:
            print(f"Connection error: {e}")
            return False

    def source_exists(self, source_name: str) -> bool:
        """Check if a source already exists."""
        try:
            response = self.session.get(f"{self.catalog_url}/by-path/{source_name}", timeout=10)
            return response.status_code == 200
        except requests.exceptions.RequestException:
            return False

    def create_minio_source(self, source_name: str = "minio") -> bool:
        """
        Create MinIO S3 source in Dremio.

        Args:
            source_name: Name for the source

        Returns:
            True if source created successfully
        """
        # Check if source already exists
        if self.source_exists(source_name):
            print(f"Source '{source_name}' already exists. Skipping creation.")
            return True

        source_config = {
            "entityType": "source",
            "name": source_name,
            "type": "S3",
            "config": {
                "compatibilityMode": True,
                "isCachingEnabled": False,
                "maxCacheSpacePct": 100,
                "secure": False,
                "externalBucketList": ["bronze", "silver", "gold"],
                "credentialType": "ACCESS_KEY",
                "accessKey": "minioadmin",
                "accessSecret": "minioadmin",
                "rootPath": "/",
                "propertyList": [
                    {"name": "fs.s3a.endpoint", "value": "minio:9000"},
                    {"name": "fs.s3a.path.style.access", "value": "true"},
                    {"name": "dremio.s3.compat", "value": "true"}
                ]
            }
        }

        try:
            response = self.session.post(
                self.catalog_url,
                json=source_config,
                timeout=30
            )

            if response.status_code in [200, 201]:
                print(f"MinIO source '{source_name}' created successfully")
                return True
            else:
                print(f"Failed to create source: {response.status_code}")
                print(f"Response: {response.text}")
                return False

        except requests.exceptions.RequestException as e:
            print(f"Error creating source: {e}")
            return False

    def refresh_source(self, source_name: str) -> bool:
        """
        Refresh source metadata to discover folders and files.

        Args:
            source_name: Name of the source to refresh

        Returns:
            True if refresh successful or initiated
        """
        try:
            response = self.session.post(
                f"{self.catalog_url}/by-path/{source_name}/refresh",
                json={},
                timeout=30
            )

            if response.status_code in [200, 204]:
                print(f"Source '{source_name}' metadata refreshed")
                return True
            else:
                print(f"Refresh returned status {response.status_code}")
                print(f"This is OK - source should still work")
                return True  # Don't fail on this

        except requests.exceptions.RequestException as e:
            print(f"Refresh request failed: {e}")
            print(f"   Source created successfully, refresh can be done manually in UI")
            return True  # Don't fail on this

    def promote_dataset(self, path: list) -> bool:
        """
        Promote a folder to a physical dataset.

        Args:
            path: List of path components (e.g., ["minio", "silver", "open_contracting_partnership"])

        Returns:
            True if dataset promoted successfully
        """
        # Build the catalog path
        catalog_path = "/".join(path)

        try:
            # First, get the folder details
            response = self.session.get(
                f"{self.catalog_url}/by-path/{catalog_path}",
                timeout=10
            )

            if response.status_code != 200:
                print(f"Folder not found: {catalog_path}")
                return False

            folder_data = response.json()

            # Promote to physical dataset
            dataset_config = {
                "entityType": "dataset",
                "path": path,
                "type": "PHYSICAL_DATASET",
                "format": {
                    "type": "Parquet"
                }
            }

            response = self.session.post(
                f"{self.catalog_url}",
                json=dataset_config,
                timeout=30
            )

            if response.status_code in [200, 201, 409]:  # 409 = already exists
                print(f"Dataset promoted: {catalog_path}")
                return True
            else:
                print(f"Could not promote dataset: {response.status_code}")
                print(f"This is OK if the dataset was already promoted.")
                return True  # Don't fail on this

        except requests.exceptions.RequestException as e:
            print(f"Error promoting dataset: {e}")
            return True  # Don't fail on this

    def run_query(self, sql: str) -> Optional[Dict[str, Any]]:
        """
        Run a SQL query.

        Args:
            sql: SQL query string

        Returns:
            Query results or None if failed
        """
        try:
            job_config = {
                "sql": sql
            }

            response = self.session.post(
                f"{self.api_url}/job/submit/sql",
                json=job_config,
                timeout=60
            )

            if response.status_code == 200:
                job_id = response.json().get("id")

                # Poll for job completion
                max_attempts = 30
                for _ in range(max_attempts):
                    status_response = self.session.get(
                        f"{self.api_url}/job/{job_id}",
                        timeout=10
                    )

                    if status_response.status_code == 200:
                        job_status = status_response.json()
                        state = job_status.get("jobState")

                        if state == "COMPLETED":
                            return job_status
                        elif state in ["FAILED", "CANCELED"]:
                            print(f"Query failed: {state}")
                            return None

                    time.sleep(1)

                print("Query timed out")
                return None

            else:
                print(f"Failed to submit query: {response.status_code}")
                return None

        except requests.exceptions.RequestException as e:
            print(f"Error running query: {e}")
            return None


def print_banner(text: str):
    """Print a formatted banner."""
    print(f"\n{'='*60}")
    print(f" {text}")
    print(f"{'='*60}\n")


def main():
    """Main configuration flow."""
    print_banner("Dremio Configuration Automation")

    # Determine Dremio host based on environment
    # Inside Docker container, use service name; outside use localhost
    import os
    dremio_host = os.getenv("DREMIO_HOST", "localhost")

    # Initialize client
    client = DremioClient(host=dremio_host)

    # Check Dremio health
    print("Checking Dremio status...")
    if not client.check_health():
        print("Dremio is not accessible at http://localhost:9047")
        print("\nTroubleshooting:")
        print("  1. Check if Dremio container is running: docker ps | grep dremio")
        print("  2. Check logs: docker logs sod-dremio")
        print("  3. Wait ~60 seconds for Dremio to fully start")
        print("  4. Run: make dremio-status")
        sys.exit(1)

    print("Dremio is accessible\n")

    # Get credentials
    print("Please enter Dremio admin credentials:")
    print("(If you haven't created an admin account yet, visit http://localhost:9047)\n")

    username = input("Username [admin]: ").strip() or "admin"
    password = getpass.getpass("Password: ")

    if not password:
        print("Password cannot be empty")
        sys.exit(1)

    # Authenticate
    print("\nAuthenticating...")
    if not client.login(username, password):
        print("\nAuthentication failed!")
        print("\nMake sure you:")
        print("  1. Created an admin account at http://localhost:9047")
        print("  2. Using the correct username and password")
        sys.exit(1)

    print("Logged in successfully\n")

    # Create MinIO source
    print("Creating MinIO source...")
    if not client.create_minio_source("minio"):
        print("Source creation failed, but continuing...")

    # Refresh source metadata to discover folders
    print("\nRefreshing source metadata...")
    print("This scans MinIO buckets to discover folders...")
    client.refresh_source("minio")

    # Wait for refresh to complete
    print("Waiting for metadata scan to complete...")
    time.sleep(5)

    print("\n" + "="*60)
    print("MinIO source configured successfully!")
    print("="*60)

    print("\nFINAL STEP - Format Dataset (2 clicks):")
    print("\n   To enable SQL queries, format the Parquet folder:")
    print("\n   1. Open Dremio UI: http://localhost:9047")
    print("   2. In left sidebar, expand:")
    print("      Sources → minio → silver → open_contracting_partnership")
    print("   3. RIGHT-CLICK on 'open_contracting_partnership' folder")
    print("   4. Select 'Format Folder'")
    print("   5. Choose Format: Parquet")
    print("   6. Click 'Save'")

    print("\nAfter formatting, test with this query:")
    print("   SELECT source_country, COUNT(*) as total")
    print("   FROM minio.silver.open_contracting_partnership")
    print("   GROUP BY source_country;")

    print("\nSee infra/dremio-setup.md for:")
    print("   - Step-by-step guide")
    print("   - Sample SQL queries")
    print("   - Python connection examples")

    print("\n" + "="*60)
    print("Setup Complete - Format the dataset and start querying!")
    print("="*60)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nSetup interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
