"""
Flask application to serve Nova Cost API endpoints
"""
import os
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from pathlib import Path
from dotenv import load_dotenv
import logging

# Import the service cancellation API
from .service_cancellation import ServiceCancellationAPI

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
dotenv_path = Path(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))).joinpath('.env')
load_dotenv(dotenv_path)

def create_app():
    """Create and configure the Flask application"""
    app = Flask(__name__)
    
    # Enable CORS for all routes and origins
    CORS(app, resources={r"/api/*": {"origins": "*"}})
    
    # Initialize the service cancellation API
    cancellation_api = ServiceCancellationAPI()
    
    # Define route for service cancellation
    @app.route('/api/cancel-service', methods=['POST'])
    def cancel_service_route():
        data = request.json
        
        # Validate request data
        if not data or 'service_name' not in data:
            return jsonify({
                'success': False,
                'message': 'Missing required parameter: service_name'
            }), 400
        
        # Extract parameters
        service_name = data.get('service_name')
        service_id = data.get('service_id')
        region = data.get('region', 'us-east-1')
        
        logger.info(f"Received cancellation request for {service_name} (ID: {service_id}) in region: {region}")
        
        # Call the API to cancel the service
        result = cancellation_api.cancel_service(service_name, service_id, region)
        
        return jsonify(result)
    
    # Define route to serve static assets for reports
    @app.route('/reports/static/<path:filename>')
    def serve_static(filename):
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        static_dir = os.path.join(base_dir, 'data', 'reports', 'static')
        return send_from_directory(static_dir, filename)
    
    # Define route to serve reports
    @app.route('/reports/<path:filename>')
    def serve_report(filename):
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        reports_dir = os.path.join(base_dir, 'data', 'reports')
        return send_from_directory(reports_dir, filename)
    
    # Define route for the dashboard
    @app.route('/dashboard')
    def dashboard():
        from datetime import date
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        reports_dir = os.path.join(base_dir, 'data', 'reports')
        today = date.today().strftime('%Y-%m-%d')
        report_filename = f'aws_cost_report_{today}.html'
        report_path = os.path.join(reports_dir, report_filename)
        
        # Check if the report exists
        if os.path.exists(report_path):
            return send_from_directory(reports_dir, report_filename)
        else:
            # Generate the report if it doesn't exist
            from ..adapters.html_report_adapter import generate_report
            generate_report()
            return send_from_directory(reports_dir, report_filename)
    
    # Health check endpoint
    @app.route('/health')
    def health_check():
        return jsonify({
            'status': 'ok',
            'version': '1.0.0'
        })
    
    # Root route redirects to dashboard
    @app.route('/')
    def index():
        return app.redirect('/dashboard')
    
    return app


def run_dev_server():
    """Run the development server"""
    app = create_app()
    app.run(debug=True, host='0.0.0.0', port=5000)


if __name__ == '__main__':
    run_dev_server()
