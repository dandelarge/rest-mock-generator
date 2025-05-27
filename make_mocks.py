import os
import requests
import json
import argparse

parser = argparse.ArgumentParser(prog='Simple Mock Generator', description='Calls an API and generates mock data based on the response.')
parser.add_argument('--config', type=str, help='Path to a configuration file for additional settings')
parser.add_argument('-u', '--user', type=str, help='Username for authentication')
parser.add_argument('-p', '--password', type=str, help='Password for authentication')
parser.add_argument('-i', '--impersonate', type=str, help='User to impersonate for the requests')
parser.add_argument('-l', '--login-url', type=str, help='URL to log in and obtain a session id')
args = parser.parse_args()

config_file = args.config if args.config else 'config.json'

config = {
    'url' : 'https://staging.fugamusic.com',
    'user' : 'danielarauz',
    'password' : '123456',
    'impersonate' : 'josef-colors',
    'login_url' : 'https://staging.fugamusic.com/ui-only/v2/login',
    'output_dir' : 'mocks',
    'headers' : {'Content-Type': 'application/json'},
    'cases' : [
        {
            'name': 'royalties_overview',
            'method': 'GET',
            'endpoint': '/api/v2/finance/royalties_overview',
            'params': {
                'organization_id': '1000689660386'
            },
            'response_file': 'royalties_overview.json'
        }
    ]
}


if not os.path.exists(config_file):
    print(f"Configuration file '{config_file}' not found. Using default settings.")
else:
    with open(config_file, 'r') as f:
        try:
            config = json.load(f)
        except json.JSONDecodeError as e:
            print(f"Error reading configuration file: {e}")


user = args.user or config.get('user')
password = args.password or config.get('password')
impersonate = args.impersonate or config.get('impersonate')
login_url = args.login_url or config.get('login_url')

def authenticate(user, password, login_url, impersonate):
    """Authenticate the user and return a session token."""
    payload = {
        'name': user,
        'password': password,
        'as': impersonate,
        'authType': 'session_and_jwt',
        'secure': 'true'
    }

    try: 
        response = requests.post(login_url, data=payload)
        response.raise_for_status()
        if response.status_code == 200:
            print("Authentication successful.")
            sessionid = response.headers.get('Set-Cookie')
            sessionid = sessionid.split(';')[0] if sessionid else None
            token = response.json().get('token')
            print(f"Token: {token}")
            print(f"Session ID: {sessionid}")
            with open('sessiondata.json', 'w') as f:
                json.dump({'sessionid': sessionid, 'token': token}, f)
            return sessionid, token
        else:
            print(f"Authentication failed with status code: {response.status_code}")
            print(f"Response: {response.text}")
            return None
    except requests.RequestException as e:
        print(f"Error during authentication: {e}")
        return None


def fetch_data(endpoint, method='GET', params=None, headers=None):
    """Fetch data from the API endpoint."""
    url = f"{config['url']}{endpoint}"
    headers = headers or config.get('headers', {})
    
    if sessionid:
        headers['Cookie'] = sessionid + ';'
    else: 
        print("No session ID available. Cannot make authenticated requests.")
        return None

    try:
        if method.upper() == 'GET':
            response = requests.get(url, params=params, headers=headers)
        elif method.upper() == 'POST':
            response = requests.post(url, json=params, headers=headers)
        else:
            print(f"Unsupported HTTP method: {method}")
            return None

        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"Error fetching data from {url}: {e}")
        return None

# make_mocks.py
def main():
    global sessionid, token

    if args.user and args.password:
        print(f"Using provided user: {args.user}")
        print(f"Using provided password: {args.password}")
        authenticate(args.user, args.password, login_url, impersonate)

    if os.path.exists('sessiondata.json'):
        print("Reading session data from 'sessiondata.json'")
    else:
        print("'sessiondata.json' not found. Creating file...")
        with open('sessiondata.json', 'w') as f:
            json.dump({'sessionid': None, 'token': None}, f)
            print("'sessiondata.json' created.")

    with open('sessiondata.json', 'r') as f:
        try:
            session_data = json.load(f)
            sessionid = session_data.get('sessionid')
            token = session_data.get('token')
        except json.JSONDecodeError as e:
            print(f"Error reading session data: {e}")
            sessionid = None
            token = None

    if not sessionid and not token:
        print("No Authentication data found. Attempting to authenticate...")
        session_data = authenticate(user, password, login_url, impersonate)
        sessionid = session_data[0] if session_data else None
        token = session_data[1] if session_data else None

    if not sessionid and not token:
        print("Authentication failed. Exiting.")
        return

    if not os.path.exists(config['output_dir']):
        os.makedirs(config['output_dir'])

    for case in config['cases']:
        response = fetch_data(case['endpoint'], case['method'], case['params'])
        if response is None:
            print(f"Failed to fetch data for case: {case['name']}")
            continue
        
        output_file = os.path.join(config['output_dir'], case['response_file'])
        with open(output_file, 'w') as f:
            json.dump(response, f, indent=4)
        
        print(f"Mock data for '{case['name']}' saved to '{output_file}'")

if __name__ == '__main__':
    main()

