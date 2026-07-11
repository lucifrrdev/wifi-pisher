import os
import sys
import subprocess
import threading
import time

# Auto-install Flask if not present
try:
    from flask import Flask, jsonify, request, render_template
except ImportError:
    print("Flask is not installed. Installing flask...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "flask"])
        from flask import Flask, jsonify, request, render_template
    except Exception as e:
        print(f"Failed to install Flask: {e}")
        print("Please install flask manually using: pip install flask")
        sys.exit(1)

app = Flask(__name__)

# Global log list for the retro console
system_logs = []

def add_log(message):
    timestamp = time.strftime('%H:%M:%S')
    log_line = f"[{timestamp}] {message}"
    print(log_line)
    system_logs.append(log_line)
    if len(system_logs) > 50:
        system_logs.pop(0)

# Initialize with startup logs
add_log("Flipper WiFi Devboard System Initializing...")
add_log("Checking for NetworkManager...")

# Check if nmcli is available
try:
    nmcli_check = subprocess.run(['nmcli', '--version'], capture_output=True, text=True)
    if nmcli_check.returncode == 0:
        add_log(f"NetworkManager detected: {nmcli_check.stdout.strip()}")
    else:
        add_log("WARNING: nmcli found but returned non-zero. Is NetworkManager running?")
except FileNotFoundError:
    add_log("ERROR: nmcli (NetworkManager) is NOT installed or not in PATH!")
    add_log("Please install NetworkManager or use a compatible OS.")

def get_wifi_interfaces():
    """
    Detects available Wi-Fi interfaces on the system using nmcli and fallback options.
    """
    interfaces = []
    # Method 1: Check via nmcli
    try:
        result = subprocess.run(
            ['nmcli', '-t', '-f', 'DEVICE,TYPE', 'device'],
            capture_output=True, text=True, check=True
        )
        for line in result.stdout.strip().split('\n'):
            if not line:
                continue
            parts = line.split(':')
            if len(parts) >= 2 and parts[1].lower() == 'wifi':
                interfaces.append(parts[0])
    except Exception:
        pass

    # Method 2: Check via Linux sysfs
    if not interfaces and os.path.exists('/sys/class/net'):
        try:
            for device in os.listdir('/sys/class/net'):
                if os.path.exists(f'/sys/class/net/{device}/wireless') or device.startswith('wlan'):
                    interfaces.append(device)
        except Exception:
            pass

    return sorted(list(set(interfaces)))

def get_interface_ip(interface):
    """
    Retrieves the IPv4 address of the specified network interface.
    """
    if not interface:
        return ""
    try:
        # Run 'ip -4 addr show dev <interface>'
        result = subprocess.run(
            ['ip', '-4', 'addr', 'show', 'dev', interface],
            capture_output=True, text=True, check=True
        )
        for line in result.stdout.split('\n'):
            if 'inet ' in line:
                parts = line.strip().split()
                if len(parts) > 1:
                    # Return IP address (split subnet mask if present)
                    return parts[1].split('/')[0]
    except Exception:
        pass
    
    return ""

def get_hotspot_status(interface='wlan0'):
    """
    Checks if there is an active wireless connection on the specified interface.
    Returns: (is_active, connection_name, ssid, password)
    """
    try:
        # Get active connections
        result = subprocess.run(
            ['nmcli', '-t', '-f', 'NAME,TYPE,DEVICE', 'connection', 'show', '--active'],
            capture_output=True, text=True, check=True
        )
        active_lines = result.stdout.strip().split('\n')
        for line in active_lines:
            if not line:
                continue
            parts = line.split(':')
            if len(parts) >= 3:
                name, conn_type, device = parts[0], parts[1], parts[2]
                # NetworkManager hotspot uses type '802-11-wireless'
                if conn_type == '802-11-wireless' and device == interface:
                    # Get SSID and password
                    ssid, pwd = get_connection_details(name)
                    return True, name, ssid, pwd
        return False, None, "", ""
    except Exception as e:
        # If error occurs (like no active connections), return inactive
        return False, None, "", ""

def get_connection_details(conn_name):
    """
    Retrieves the SSID and password of a specific NetworkManager connection.
    """
    ssid = conn_name
    password = ""
    try:
        # Get SSID
        res_ssid = subprocess.run(
            ['nmcli', '-s', '-g', '802-11-wireless.ssid', 'connection', 'show', conn_name],
            capture_output=True, text=True
        )
        if res_ssid.returncode == 0:
            ssid = res_ssid.stdout.strip()
            
        # Get PSK (will fail or be empty for open networks)
        res_psk = subprocess.run(
            ['nmcli', '-s', '-g', '802-11-wireless-security.psk', 'connection', 'show', conn_name],
            capture_output=True, text=True
        )
        if res_psk.returncode == 0:
            password = res_psk.stdout.strip()
    except Exception:
        pass
    return ssid, password

def get_connected_clients(interface='wlan0'):
    """
    Counts connected clients using 'ip neigh show'.
    """
    try:
        result = subprocess.run(['ip', 'neigh', 'show', 'dev', interface], capture_output=True, text=True)
        count = 0
        clients = []
        for line in result.stdout.strip().split('\n'):
            if not line:
                continue
            if 'lladdr' in line and 'FAILED' not in line:
                parts = line.split()
                ip = parts[0]
                mac = "[Unknown]"
                for i, part in enumerate(parts):
                    if part == 'lladdr' and i + 1 < len(parts):
                        mac = parts[i+1]
                        break
                clients.append({'ip': ip, 'mac': mac})
                count += 1
        return count, clients
    except Exception as e:
        return 0, []

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/status', methods=['GET'])
def api_status():
    interface = request.args.get('interface', 'wlan0')
    active, conn_name, ssid, password = get_hotspot_status(interface)
    client_count, clients = get_connected_clients(interface)
    
    # Build list of interfaces with their IP addresses
    interfaces_list = get_wifi_interfaces()
    interfaces_data = []
    for iface in interfaces_list:
        ip = get_interface_ip(iface)
        interfaces_data.append({'name': iface, 'ip': ip})
    
    return jsonify({
        'active': active,
        'ssid': ssid,
        'password': password,
        'interface': interface,
        'interfaces': interfaces_data,
        'clients_count': client_count,
        'clients': clients,
        'logs': system_logs
    })

@app.route('/api/start', methods=['POST'])
def api_start():
    data = request.json or {}
    ssid = data.get('ssid')
    password = data.get('password')
    interface = data.get('interface', 'wlan0')
    
    if not ssid:
        return jsonify({'success': False, 'error': 'SSID is required'}), 400
        
    if password and len(password) < 8:
        return jsonify({'success': False, 'error': 'Password must be at least 8 characters long'}), 400

    if password:
        add_log(f"Starting WPA2 Hotspot SSID: '{ssid}' on interface '{interface}'...")
    else:
        add_log(f"Starting OPEN Hotspot SSID: '{ssid}' on interface '{interface}'...")
    
    # Run in a background thread so the HTTP response is not blocked
    def start_thread():
        # Step 1: Clean up any old connection profile named 'Hotspot'
        add_log("Cleaning up old connection profiles...")
        subprocess.run(['sudo', 'nmcli', 'connection', 'delete', 'Hotspot'], capture_output=True)
        
        # Step 2: Start the hotspot
        if password:
            add_log(f"Running nmcli wifi hotspot command...")
            cmd = ['sudo', 'nmcli', 'device', 'wifi', 'hotspot', 'ssid', ssid, 'password', password, 'ifname', interface]
            result = subprocess.run(cmd, capture_output=True, text=True)
        else:
            add_log(f"Creating open hotspot connection profile...")
            # Create connection profile
            subprocess.run(['sudo', 'nmcli', 'connection', 'add', 'type', 'wifi', 'ifname', interface, 'con-name', 'Hotspot', 'autoconnect', 'no', 'ssid', ssid, 'mode', 'ap'], capture_output=True)
            # Modify connection settings
            subprocess.run(['sudo', 'nmcli', 'connection', 'modify', 'Hotspot', '802-11-wireless.mode', 'ap', 'ipv4.method', 'shared'], capture_output=True)
            # Remove any security configuration to prevent NM from asking for WEP/WPA keys
            subprocess.run(['sudo', 'nmcli', 'connection', 'modify', 'Hotspot', 'remove', '802-11-wireless-security'], capture_output=True)
            # Bring connection up
            add_log("Bringing open hotspot connection up...")
            result = subprocess.run(['sudo', 'nmcli', 'connection', 'up', 'Hotspot'], capture_output=True, text=True)
        
        if result.returncode == 0:
            add_log("SUCCESS: Hotspot started successfully!")
            add_log(f"IP Address: 192.168.4.1 (typical for nmcli)")
        else:
            add_log(f"ERROR: Failed to start hotspot.")
            add_log(f"Details: {result.stderr.strip() or result.stdout.strip()}")
            
    threading.Thread(target=start_thread).start()
    return jsonify({'success': True, 'message': 'Hotspot starting process initiated.'})

@app.route('/api/stop', methods=['POST'])
def api_stop():
    interface = request.json.get('interface', 'wlan0')
    add_log("Stopping Hotspot...")
    
    def stop_thread():
        active, conn_name, _, _ = get_hotspot_status(interface)
        if active:
            add_log(f"Active hotspot connection '{conn_name}' found. Disabling...")
            # Down the connection
            res_down = subprocess.run(['sudo', 'nmcli', 'connection', 'down', conn_name], capture_output=True, text=True)
            # Delete the profile to clean up
            res_del = subprocess.run(['sudo', 'nmcli', 'connection', 'delete', conn_name], capture_output=True, text=True)
            # Force disconnect the device to be absolutely sure the hotspot stops broadcasting
            subprocess.run(['sudo', 'nmcli', 'device', 'disconnect', interface], capture_output=True)
            
            if res_down.returncode == 0:
                add_log(f"SUCCESS: Hotspot disabled on {interface}.")
            else:
                add_log(f"WARNING: Down command output: {res_down.stderr.strip()}")
        else:
            add_log(f"No active hotspot connection found on {interface}. Attempting hard interface disconnect...")
            # Fallback hard disconnect
            subprocess.run(['sudo', 'nmcli', 'device', 'disconnect', interface], capture_output=True)
            add_log(f"Interface {interface} disconnected.")
            
    threading.Thread(target=stop_thread).start()
    return jsonify({'success': True, 'message': 'Hotspot stopping process initiated.'})

if __name__ == '__main__':
    # Binds to all interfaces on port 5002
    print("--------------------------------------------------")
    print(" Flipper Zero Hotspot Web Server running!")
    print(" Access it via: http://<raspberry-pi-ip>:5002")
    print("--------------------------------------------------")
    app.run(host='0.0.0.0', port=5002, debug=False)
