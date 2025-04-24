"""
Service Cancellation API - Provides endpoints for canceling AWS services
"""
import boto3
import json
import os
import logging
from typing import Dict, Any, List, Optional
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)

class ServiceCancellationAPI:
    """API for canceling AWS services directly from the cost dashboard"""
    
    def __init__(self):
        """Initialize the API with AWS session"""
        self.session = boto3.Session()
    
    def cancel_service(self, service_name: str, service_id: str = None, region: str = "us-east-1") -> Dict[str, Any]:
        """
        Cancel an AWS service based on its name and optional ID
        
        Args:
            service_name: Name of the service to cancel (e.g., "Amazon OpenSearch Service")
            service_id: ID of the specific resource to cancel (optional)
            region: AWS region where the service is deployed
            
        Returns:
            Dictionary with cancellation status and details
        """
        logger.info(f"Canceling service: {service_name} (ID: {service_id}) in region: {region}")
        
        try:
            # Create a session for the specified region
            session = boto3.Session(region_name=region)
            
            # Map service name to appropriate cancellation function
            cancellation_functions = {
                "Amazon OpenSearch Service": self._cancel_opensearch,
                "OpenSearch Serverless": self._cancel_opensearch_serverless,
                "Amazon Redshift": self._cancel_redshift,
                "AWS Lambda": self._cancel_lambda,
                "Amazon EC2": self._cancel_ec2,
                "Amazon RDS": self._cancel_rds,
                "Amazon S3": self._cancel_s3
            }
            
            # Get the appropriate cancellation function or use default
            cancel_func = cancellation_functions.get(
                service_name, 
                self._default_cancellation
            )
            
            # Call the specific cancellation function
            result = cancel_func(session, service_id, region)
            
            return {
                "success": True,
                "message": f"Successfully initiated cancellation for {service_name}",
                "details": result
            }
            
        except ClientError as e:
            logger.error(f"AWS client error canceling {service_name}: {str(e)}")
            return {
                "success": False,
                "message": f"Error canceling {service_name}: {str(e)}",
                "error_code": e.response['Error']['Code'] if hasattr(e, 'response') else "UnknownError"
            }
        except Exception as e:
            logger.error(f"Error canceling {service_name}: {str(e)}")
            return {
                "success": False,
                "message": f"Error canceling {service_name}: {str(e)}",
                "error_code": "UnknownError"
            }
    
    def _cancel_opensearch(self, session, domain_name: str, region: str) -> Dict[str, Any]:
        """Cancel an OpenSearch domain"""
        if not domain_name:
            # List all domains if no specific one provided
            client = session.client('opensearch')
            domains = client.list_domain_names()
            return {"domains": domains["DomainNames"], "action": "list_only"}
        
        # Cancel specific domain
        client = session.client('opensearch')
        response = client.delete_domain(
            DomainName=domain_name
        )
        
        return {
            "domain_name": domain_name,
            "deletion_status": response.get("DomainStatus", {}),
            "cancellation_time": response.get("DeletionDate", ""),
            "action": "deleted"
        }
    
    def _cancel_opensearch_serverless(self, session, collection_id: str, region: str) -> Dict[str, Any]:
        """Cancel an OpenSearch Serverless collection"""
        client = session.client('opensearchserverless')
        
        if not collection_id:
            # List all collections if no specific one provided
            collections = client.list_collections()
            return {"collections": collections.get("collectionSummaries", []), "action": "list_only"}
        
        # Cancel specific collection
        response = client.delete_collection(
            id=collection_id
        )
        
        return {
            "collection_id": collection_id,
            "deletion_status": response.get("status", ""),
            "cancellation_time": response.get("deleteDate", ""),
            "action": "deleted"
        }
    
    def _cancel_redshift(self, session, cluster_id: str, region: str) -> Dict[str, Any]:
        """Cancel a Redshift cluster"""
        client = session.client('redshift')
        
        if not cluster_id:
            # List all clusters if no specific one provided
            clusters = client.describe_clusters()
            return {"clusters": clusters.get("Clusters", []), "action": "list_only"}
        
        # Cancel specific cluster
        response = client.delete_cluster(
            ClusterIdentifier=cluster_id,
            SkipFinalClusterSnapshot=True
        )
        
        return {
            "cluster_id": cluster_id,
            "deletion_status": response.get("Cluster", {}).get("ClusterStatus", ""),
            "action": "deleted"
        }
    
    def _cancel_lambda(self, session, function_name: str, region: str) -> Dict[str, Any]:
        """Cancel a Lambda function"""
        client = session.client('lambda')
        
        if not function_name:
            # List all functions if no specific one provided
            functions = client.list_functions()
            return {"functions": functions.get("Functions", []), "action": "list_only"}
        
        # Cancel specific function
        response = client.delete_function(
            FunctionName=function_name
        )
        
        return {
            "function_name": function_name,
            "action": "deleted"
        }
    
    def _cancel_ec2(self, session, instance_id: str, region: str) -> Dict[str, Any]:
        """Terminate an EC2 instance"""
        client = session.client('ec2')
        
        if not instance_id:
            # List all instances if no specific one provided
            instances = client.describe_instances()
            return {"instances": instances.get("Reservations", []), "action": "list_only"}
        
        # Terminate specific instance
        response = client.terminate_instances(
            InstanceIds=[instance_id]
        )
        
        return {
            "instance_id": instance_id,
            "termination_status": response.get("TerminatingInstances", []),
            "action": "terminated"
        }
    
    def _cancel_rds(self, session, db_instance_id: str, region: str) -> Dict[str, Any]:
        """Cancel an RDS database instance"""
        client = session.client('rds')
        
        if not db_instance_id:
            # List all DB instances if no specific one provided
            instances = client.describe_db_instances()
            return {"db_instances": instances.get("DBInstances", []), "action": "list_only"}
        
        # Cancel specific DB instance
        response = client.delete_db_instance(
            DBInstanceIdentifier=db_instance_id,
            SkipFinalSnapshot=True,
            DeleteAutomatedBackups=True
        )
        
        return {
            "db_instance_id": db_instance_id,
            "deletion_status": response.get("DBInstance", {}).get("DBInstanceStatus", ""),
            "action": "deleted"
        }
    
    def _cancel_s3(self, session, bucket_name: str, region: str) -> Dict[str, Any]:
        """Delete an S3 bucket (note: bucket must be empty)"""
        client = session.client('s3')
        
        if not bucket_name:
            # List all buckets if no specific one provided
            buckets = client.list_buckets()
            return {"buckets": buckets.get("Buckets", []), "action": "list_only"}
        
        # First empty the bucket
        try:
            # List all objects in the bucket
            objects = client.list_objects_v2(Bucket=bucket_name)
            if 'Contents' in objects:
                # Delete all objects in the bucket
                client.delete_objects(
                    Bucket=bucket_name,
                    Delete={
                        'Objects': [{'Key': obj['Key']} for obj in objects['Contents']]
                    }
                )
                
            # Delete the bucket
            response = client.delete_bucket(
                Bucket=bucket_name
            )
            
            return {
                "bucket_name": bucket_name,
                "action": "deleted"
            }
        except ClientError as e:
            return {
                "bucket_name": bucket_name,
                "error": str(e),
                "action": "error"
            }
    
    def _default_cancellation(self, session, resource_id: str, region: str) -> Dict[str, Any]:
        """Default cancellation for services without specific implementation"""
        return {
            "error": "Cancellation not implemented for this service type",
            "service_id": resource_id,
            "region": region,
            "action": "not_implemented"
        }


# Create a Flask route to handle the cancellation requests
def create_cancellation_endpoint():
    """
    Create a Flask route to handle service cancellation requests
    
    This function should be called in the app's route registration
    """
    from flask import Flask, request, jsonify
    
    app = Flask(__name__)
    cancellation_api = ServiceCancellationAPI()
    
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
        
        # Call the API to cancel the service
        result = cancellation_api.cancel_service(service_name, service_id, region)
        
        return jsonify(result)
    
    return app


# Function to directly call the cancellation API without a web server
def cancel_service_directly(service_name: str, service_id: str = None, region: str = "us-east-1") -> Dict[str, Any]:
    """
    Directly cancel an AWS service without going through a web API
    
    Args:
        service_name: Name of the service to cancel
        service_id: ID of the specific resource to cancel (optional)
        region: AWS region where the resource is deployed
        
    Returns:
        Dictionary with cancellation status and details
    """
    api = ServiceCancellationAPI()
    return api.cancel_service(service_name, service_id, region)
