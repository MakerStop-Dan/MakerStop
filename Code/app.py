from flask import Flask, render_template, request, jsonify, send_from_directory
import json
import os
from datetime import datetime
import csv

app = Flask(__name__)

CUTLIST_DIR = '/home/makerstop/Code/cutlists'
os.makedirs(CUTLIST_DIR, exist_ok=True)
os.makedirs('static', exist_ok=True)
os.makedirs('templates', exist_ok=True)

@app.route('/')
def index():
    """Serve the main cutlist creation interface"""
    return render_template('index.html')

@app.route('/api/cutlist', methods=['POST'])
def receive_cutlist():
    """Accept cutlist data from the web interface"""
    txt_filename = None  # Initialize to avoid any reference errors
    
    try:
        cutlist_data = request.json
        
        # Generate timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # JSON filename
        json_filename = f"cutlist_{timestamp}.json"
        json_filepath = os.path.join(CUTLIST_DIR, json_filename)
        
        # TXT filename based on project name
        project_name = cutlist_data.get('project_name', 'Unnamed_Project')
        clean_project_name = "".join(c for c in project_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
        clean_project_name = clean_project_name.replace(' ', '_')
        if not clean_project_name:  # Fallback if name becomes empty
            clean_project_name = 'Unnamed_Project'
        
        txt_filename = f"{clean_project_name}.txt"
        txt_filepath = os.path.join(CUTLIST_DIR, txt_filename)
        
        # Add txt filename to data for reference
        cutlist_data['txt_filename'] = txt_filename
        
        # Save JSON file
        with open(json_filepath, 'w') as f:
            json.dump(cutlist_data, f, indent=2)
        
        # Create TXT file
        with open(txt_filepath, 'w') as txtfile:
            if 'cuts' in cutlist_data and cutlist_data['cuts']:
                for cut in cutlist_data['cuts']:
                    length = cut.get('length', 0)
                    description = cut.get('description', 'No description')
                    material = cut.get('material', 'No material')
                    quantity = cut.get('quantity', 1)
                    
                    # Format: Length : Description - Material
                    cut_line = f"{length} : {description} - {material}\n"
                    
                    # Write the line multiple times based on quantity
                    for _ in range(quantity):
                        txtfile.write(cut_line)
        
        print(f"Cutlist saved: {json_filename}")
        print(f"Text file saved: {txt_filename}")
        print(f"Project: {cutlist_data.get('project_name', 'Unnamed')}")
        print(f"Number of cuts: {len(cutlist_data.get('cuts', []))}")
        
        return jsonify({
            'status': 'success',
            'message': 'Cutlist received and saved',
            'filename': json_filename,
            'txt_filename': txt_filename,
            'timestamp': timestamp
        })
        
    except Exception as e:
        print(f"Error processing cutlist: {e}")
        error_response = {
            'status': 'error',
            'message': str(e)
        }
        if txt_filename:
            error_response['txt_filename'] = txt_filename
        return jsonify(error_response), 400

@app.route('/api/cutlists', methods=['GET'])
def list_cutlists():
    """Get list of saved cutlists"""
    try:
        cutlist_files = []
        
        if not os.path.exists(CUTLIST_DIR):
            return jsonify([])
        for filename in os.listdir(CUTLIST_DIR):
            if filename.endswith('.json'):
                try:
                    filepath = os.path.join(CUTLIST_DIR, filename)
                    stat = os.stat(filepath)
                    
                    # Load basic info from the file
                    with open(filepath, 'r') as f:
                        data = json.load(f)
                    
                    # Generate txt_filename if it doesn't exist
                    txt_filename = data.get('txt_filename')
                    if not txt_filename:
                        # Create a fallback txt filename
                        base_name = filename.replace('cutlist_', '').replace('.json', '')
                        project_name = data.get('project_name', 'Unnamed_Project')
                        clean_name = "".join(c for c in project_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
                        clean_name = clean_name.replace(' ', '_')
                        if not clean_name:
                            clean_name = 'Unnamed_Project'
                        txt_filename = f"{clean_name}.txt"
                    
                    cutlist_files.append({
                        'filename': filename,
                        'txt_filename': txt_filename,
                        'project_name': data.get('project_name', 'Unnamed'),
                        'created': datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S'),
                        'cut_count': len(data.get('cuts', []))
                    })
                    
                except Exception as file_error:
                    print(f"Error reading file {filename}: {file_error}")
                    continue
        
        # Sort by creation time, newest first
        cutlist_files.sort(key=lambda x: x['created'], reverse=True)
        
        return jsonify(cutlist_files)
        
    except Exception as e:
        print(f"Error in list_cutlists: {e}")
        return jsonify({'error': str(e)}), 400

@app.route('/api/cutlist/<filename>', methods=['GET'])
def get_cutlist(filename):
    """Get a specific cutlist file"""
    try:
        filepath = os.path.join(CUTLIST_DIR, filename)
        if not os.path.exists(filepath):
            return jsonify({'error': 'File not found'}), 404
            
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        return jsonify(data)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/download/<filename>')
def download_cutlist(filename):
    """Download a cutlist file"""
    try:
        return send_from_directory(CUTLIST_DIR, filename)
    except Exception as e:
        return jsonify({'error': str(e)}), 404

@app.route('/status')
def status():
    """Simple status endpoint"""
    try:
        cutlist_count = 0
        if os.path.exists('cutlists'):
            cutlist_count = len([f for f in os.listdir('cutlists') if f.endswith('.json')])
        
        return jsonify({
            'status': 'online',
            'cutlists_stored': cutlist_count,
            'server_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
# Add this route to your existing Flask app (after your other routes)

@app.route('/api/cutlist/txt/<txt_filename>', methods=['GET'])
def get_cutlist_txt(txt_filename):
    """Load a txt cutlist file and parse it for editing"""
    try:
        txt_filepath = os.path.join(CUTLIST_DIR, txt_filename)
        if not os.path.exists(txt_filepath):
            return jsonify({'error': 'TXT file not found'}), 404
        
        cuts = []
        cut_counts = {}  # Track quantities for duplicate cuts
        
        with open(txt_filepath, 'r') as f:
            for line in f:
                line = line.strip()
                if line:
                    # Parse format: "Length : Description - Material"
                    try:
                        if ' : ' in line and ' - ' in line:
                            length_part, rest = line.split(' : ', 1)
                            description, material = rest.split(' - ', 1)
                            
                            length = length_part.strip()
                            description = description.strip()
                            material = material.strip()
                            
                            # Create a unique key for this cut
                            cut_key = f"{length}|{description}|{material}"
                            
                            if cut_key in cut_counts:
                                cut_counts[cut_key] += 1
                            else:
                                cut_counts[cut_key] = 1
                                cuts.append({
                                    'length': length,
                                    'description': description,
                                    'material': material,
                                    'quantity': 1  # Will be updated below
                                })
                    except ValueError:
                        # Skip malformed lines
                        continue
        
        # Update quantities based on counts
        for cut in cuts:
            cut_key = f"{cut['length']}|{cut['description']}|{cut['material']}"
            cut['quantity'] = cut_counts[cut_key]
        
        # Extract project name from filename (remove .txt extension)
        project_name = txt_filename.replace('.txt', '').replace('_', ' ')
        
        return jsonify({
            'project_name': project_name,
            'cuts': cuts,
            'txt_filename': txt_filename
        })
        
    except Exception as e:
        print(f"Error reading txt file: {e}")
        return jsonify({'error': str(e)}), 400

if __name__ == '__main__':
    print("Starting Cutlist Server...")
    print("Access the web interface at: http://localhost:5000")
    print("Or from other devices at: http://[raspberry-pi-ip]:5000")
    
    # Run on all interfaces so it's accessible from other devices on the network
    app.run(host='0.0.0.0', port=5000, debug=True)