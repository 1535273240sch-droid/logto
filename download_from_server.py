#!/usr/bin/env python3
import paramiko
import os
import sys
from scp import SCPClient

def download_all_files(host, port, username, password, local_dir):
    """Download all files from remote server to local directory"""
    try:
        # Create SSH client
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        print(f"Connecting to {host}:{port} as {username}...")
        ssh.connect(host, port=port, username=username, password=password)
        print("Connected successfully!")
        
        # Create SCP client
        with SCPClient(ssh.get_transport(), socket_timeout=60) as scp:
            # Get all files in home directory
            print("Listing remote files...")
            stdin, stdout, stderr = ssh.exec_command('find ~ -type f | head -1000')
            files = stdout.read().decode().splitlines()
            
            if not files:
                print("No files found in home directory.")
                # Try root directory instead
                stdin, stdout, stderr = ssh.exec_command('find / -type f 2>/dev/null | head -1000')
                files = stdout.read().decode().splitlines()
            
            print(f"Found {len(files)} files to download.")
            
            # Create local directory if it doesn't exist
            os.makedirs(local_dir, exist_ok=True)
            
            # Download each file
            downloaded_count = 0
            skipped_count = 0
            
            for remote_path in files:
                # Skip system directories that we don't need
                if any(remote_path.startswith(prefix) for prefix in [
                    '/proc/', '/sys/', '/dev/', '/run/', 
                    '/proc', '/sys', '/dev', '/run',
                    '/var/lib/', '/var/run/', '/tmp/'
                ]):
                    skipped_count += 1
                    continue
                
                # Preserve directory structure relative to root
                if remote_path.startswith('/'):
                    relative_path = remote_path.lstrip('/')
                else:
                    relative_path = remote_path
                
                local_path = os.path.join(local_dir, relative_path)
                local_file_dir = os.path.dirname(local_path)
                
                try:
                    os.makedirs(local_file_dir, exist_ok=True)
                    scp.get(remote_path, local_path, recursive=False)
                    print(f"✓ {remote_path} -> {local_path}")
                    downloaded_count += 1
                except Exception as e:
                    print(f"✗ Failed to download {remote_path}: {e}")
                    skipped_count += 1
            
            print(f"\nDownload complete: {downloaded_count} files downloaded, {skipped_count} skipped.")
        
        ssh.close()
        return True
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return False

if __name__ == "__main__":
    # Server configuration
    HOST = "1.14.125.204"
    PORT = 22
    USERNAME = "ubuntu"
    PASSWORD = "Sch13255884503"
    LOCAL_DIR = "/workspace/server_files"
    
    success = download_all_files(HOST, PORT, USERNAME, PASSWORD, LOCAL_DIR)
    sys.exit(0 if success else 1)
