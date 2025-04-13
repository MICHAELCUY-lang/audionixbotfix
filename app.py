import os
from flask import Flask, render_template, request, jsonify, redirect, url_for
import logging
from services.youtube_service import search_youtube, download_from_youtube
from services.spotify_service import search_spotify, download_from_spotify
from utils.converter import convert_mp3_to_mp4, convert_mp4_to_mp3
import tempfile

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Create the Flask application
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "music-bot-session-key")

@app.route('/')
def home():
    """Render the home page."""
    return render_template('index.html')

@app.route('/search', methods=['GET', 'POST'])
def search():
    """Handle search requests."""
    if request.method == 'POST':
        query = request.form.get('query')
        platform = request.form.get('platform', 'youtube')
        
        if not query:
            return jsonify({'error': 'No search query provided'}), 400
        
        # Search based on the platform
        results = []
        if platform == 'youtube':
            results = search_youtube(query)
        elif platform == 'spotify':
            results = search_spotify(query)
        
        return jsonify({'results': results})
    
    # GET request, show search page
    return render_template('search.html')

@app.route('/download/<platform>/<track_id>')
def download(platform, track_id):
    """Handle download requests."""
    try:
        filepath = None
        if platform == 'youtube':
            filepath = download_from_youtube(track_id)
        elif platform == 'spotify':
            filepath = download_from_spotify(track_id)
        
        if not filepath:
            return jsonify({'error': 'Failed to download the file'}), 500
        
        # Return a download link (this is simplified)
        return jsonify({'download_url': url_for('serve_file', filename=os.path.basename(filepath))})
    
    except Exception as e:
        logger.error(f"Download error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/convert', methods=['GET', 'POST'])
def convert():
    """Handle conversion requests."""
    if request.method == 'POST':
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        conversion_type = request.form.get('conversion_type')
        
        if not file or not conversion_type:
            return jsonify({'error': 'Missing file or conversion type'}), 400
        
        # Save the uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1]) as temp:
            file.save(temp.name)
            input_filepath = temp.name
        
        try:
            output_filepath = None
            if conversion_type == 'mp3_to_mp4':
                output_filepath = convert_mp3_to_mp4(input_filepath)
            elif conversion_type == 'mp4_to_mp3':
                output_filepath = convert_mp4_to_mp3(input_filepath)
            
            if not output_filepath:
                return jsonify({'error': 'Conversion failed'}), 500
            
            # Clean up input file
            if os.path.exists(input_filepath):
                os.remove(input_filepath)
            
            # Return a download link (this is simplified)
            return jsonify({'download_url': url_for('serve_file', filename=os.path.basename(output_filepath))})
        
        except Exception as e:
            logger.error(f"Conversion error: {e}")
            # Clean up temporary files
            if os.path.exists(input_filepath):
                os.remove(input_filepath)
            return jsonify({'error': str(e)}), 500
    
    # GET request, show conversion page
    return render_template('convert.html')

@app.route('/file/<filename>')
def serve_file(filename):
    """Serve a file for download."""
    # This is a simplified version; in a real app, you'd need a proper way to manage and serve files
    return f"Download link for: {filename}"

# Create the templates directory and basic templates
os.makedirs('templates', exist_ok=True)

if __name__ == '__main__':
    # Create a simple HTML template if it doesn't exist
    if not os.path.exists('templates/index.html'):
        with open('templates/index.html', 'w') as f:
            f.write("""
<!DOCTYPE html>
<html>
<head>
    <title>Music Bot Web Interface</title>
    <link href="https://cdn.replit.com/agent/bootstrap-agent-dark-theme.min.css" rel="stylesheet">
</head>
<body>
    <div class="container mt-5">
        <h1>Music Bot Web Interface</h1>
        <p>This is a web interface for the Music Bot. Use the following functionality:</p>
        
        <div class="row mt-4">
            <div class="col-md-6">
                <div class="card">
                    <div class="card-body">
                        <h5 class="card-title">Search and Download</h5>
                        <p class="card-text">Search for music on YouTube or Spotify and download it.</p>
                        <a href="/search" class="btn btn-primary">Go to Search</a>
                    </div>
                </div>
            </div>
            
            <div class="col-md-6">
                <div class="card">
                    <div class="card-body">
                        <h5 class="card-title">Convert Files</h5>
                        <p class="card-text">Convert between MP3 and MP4 formats.</p>
                        <a href="/convert" class="btn btn-primary">Go to Converter</a>
                    </div>
                </div>
            </div>
        </div>
    </div>
</body>
</html>
            """)
    
    if not os.path.exists('templates/search.html'):
        with open('templates/search.html', 'w') as f:
            f.write("""
<!DOCTYPE html>
<html>
<head>
    <title>Search Music - Music Bot</title>
    <link href="https://cdn.replit.com/agent/bootstrap-agent-dark-theme.min.css" rel="stylesheet">
</head>
<body>
    <div class="container mt-5">
        <h1>Search for Music</h1>
        
        <form id="searchForm" class="mt-4">
            <div class="mb-3">
                <label for="query" class="form-label">Search Query</label>
                <input type="text" class="form-control" id="query" name="query" required>
            </div>
            
            <div class="mb-3">
                <label class="form-label">Platform</label>
                <div class="form-check">
                    <input class="form-check-input" type="radio" name="platform" id="platformYoutube" value="youtube" checked>
                    <label class="form-check-label" for="platformYoutube">
                        YouTube
                    </label>
                </div>
                <div class="form-check">
                    <input class="form-check-input" type="radio" name="platform" id="platformSpotify" value="spotify">
                    <label class="form-check-label" for="platformSpotify">
                        Spotify
                    </label>
                </div>
            </div>
            
            <button type="submit" class="btn btn-primary">Search</button>
            <a href="/" class="btn btn-secondary">Back to Home</a>
        </form>
        
        <div id="results" class="mt-4"></div>
        
        <script>
            document.getElementById('searchForm').addEventListener('submit', function(e) {
                e.preventDefault();
                
                const query = document.getElementById('query').value;
                const platform = document.querySelector('input[name="platform"]:checked').value;
                
                // Show loading indicator
                const resultsDiv = document.getElementById('results');
                resultsDiv.innerHTML = '<div class="d-flex justify-content-center"><div class="spinner-border" role="status"><span class="visually-hidden">Loading...</span></div></div>';
                
                // Make API request
                fetch('/search', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/x-www-form-urlencoded',
                    },
                    body: new URLSearchParams({
                        query: query,
                        platform: platform
                    })
                })
                .then(response => response.json())
                .then(data => {
                    if (data.error) {
                        resultsDiv.innerHTML = `<div class="alert alert-danger">${data.error}</div>`;
                        return;
                    }
                    
                    if (!data.results || data.results.length === 0) {
                        resultsDiv.innerHTML = '<div class="alert alert-info">No results found</div>';
                        return;
                    }
                    
                    // Display results
                    let html = '<h2>Results</h2><div class="list-group">';
                    
                    data.results.forEach(result => {
                        html += `
                            <div class="list-group-item">
                                <div class="d-flex w-100 justify-content-between">
                                    <h5 class="mb-1">${result.title}</h5>
                                </div>
                                <p class="mb-1">Artist: ${result.artist}</p>
                                <a href="/download/${result.platform}/${result.id}" class="btn btn-sm btn-success">Download</a>
                            </div>
                        `;
                    });
                    
                    html += '</div>';
                    resultsDiv.innerHTML = html;
                })
                .catch(error => {
                    resultsDiv.innerHTML = `<div class="alert alert-danger">Error: ${error.message}</div>`;
                });
            });
        </script>
    </div>
</body>
</html>
            """)
    
    if not os.path.exists('templates/convert.html'):
        with open('templates/convert.html', 'w') as f:
            f.write("""
<!DOCTYPE html>
<html>
<head>
    <title>Convert Files - Music Bot</title>
    <link href="https://cdn.replit.com/agent/bootstrap-agent-dark-theme.min.css" rel="stylesheet">
</head>
<body>
    <div class="container mt-5">
        <h1>Convert Media Files</h1>
        
        <form id="convertForm" class="mt-4" enctype="multipart/form-data">
            <div class="mb-3">
                <label for="file" class="form-label">Upload File</label>
                <input type="file" class="form-control" id="file" name="file" required>
            </div>
            
            <div class="mb-3">
                <label class="form-label">Conversion Type</label>
                <div class="form-check">
                    <input class="form-check-input" type="radio" name="conversion_type" id="mp3ToMp4" value="mp3_to_mp4" checked>
                    <label class="form-check-label" for="mp3ToMp4">
                        MP3 to MP4
                    </label>
                </div>
                <div class="form-check">
                    <input class="form-check-input" type="radio" name="conversion_type" id="mp4ToMp3" value="mp4_to_mp3">
                    <label class="form-check-label" for="mp4ToMp3">
                        MP4 to MP3
                    </label>
                </div>
            </div>
            
            <button type="submit" class="btn btn-primary">Convert</button>
            <a href="/" class="btn btn-secondary">Back to Home</a>
        </form>
        
        <div id="conversionResult" class="mt-4"></div>
        
        <script>
            document.getElementById('convertForm').addEventListener('submit', function(e) {
                e.preventDefault();
                
                const fileInput = document.getElementById('file');
                const conversionType = document.querySelector('input[name="conversion_type"]:checked').value;
                
                if (!fileInput.files || fileInput.files.length === 0) {
                    alert('Please select a file to convert');
                    return;
                }
                
                // Create form data
                const formData = new FormData();
                formData.append('file', fileInput.files[0]);
                formData.append('conversion_type', conversionType);
                
                // Show loading indicator
                const resultDiv = document.getElementById('conversionResult');
                resultDiv.innerHTML = '<div class="d-flex justify-content-center"><div class="spinner-border" role="status"><span class="visually-hidden">Loading...</span></div></div>';
                
                // Submit form
                fetch('/convert', {
                    method: 'POST',
                    body: formData
                })
                .then(response => response.json())
                .then(data => {
                    if (data.error) {
                        resultDiv.innerHTML = `<div class="alert alert-danger">${data.error}</div>`;
                        return;
                    }
                    
                    if (data.download_url) {
                        resultDiv.innerHTML = `
                            <div class="alert alert-success">
                                Conversion successful! 
                                <a href="${data.download_url}" class="btn btn-sm btn-primary">Download</a>
                            </div>
                        `;
                    }
                })
                .catch(error => {
                    resultDiv.innerHTML = `<div class="alert alert-danger">Error: ${error.message}</div>`;
                });
            });
        </script>
    </div>
</body>
</html>
            """)
    
    # Run the app
    app.run(host='0.0.0.0', port=5000, debug=True)