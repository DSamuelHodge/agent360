import pytest
from kubernetes import client, config
from kubernetes.client.rest import ApiException

class TestKubernetesResources:
    @classmethod
    def setup_class(cls):
        """Set up Kubernetes client configuration."""
        try:
            config.load_kube_config()
        except Exception:
            config.load_incluster_config()
        cls.v1 = client.CoreV1Api()
        cls.apps_v1 = client.AppsV1Api()
        cls.namespace = "agent360"

    def test_namespace_exists(self):
        """Test if the agent360 namespace exists."""
        namespaces = self.v1.list_namespace()
        namespace_names = [ns.metadata.name for ns in namespaces.items]
        assert self.namespace in namespace_names

    def test_deployments_running(self):
        """Test if all required deployments are running."""
        required_deployments = ["agent360-api", "redis", "cassandra", "temporal"]
        
        try:
            deployments = self.apps_v1.list_namespaced_deployment(self.namespace)
            deployment_names = [dep.metadata.name for dep in deployments.items]
            
            for dep in required_deployments:
                assert dep in deployment_names, f"Deployment {dep} not found"
                
                # Check deployment status
                deployment = self.apps_v1.read_namespaced_deployment(dep, self.namespace)
                assert deployment.status.ready_replicas == deployment.status.replicas, \
                    f"Deployment {dep} not fully ready"
        except ApiException as e:
            pytest.fail(f"Failed to check deployments: {e}")

    def test_services_running(self):
        """Test if all required services are running."""
        required_services = ["agent360-api", "redis", "cassandra", "temporal"]
        
        try:
            services = self.v1.list_namespaced_service(self.namespace)
            service_names = [svc.metadata.name for svc in services.items]
            
            for svc in required_services:
                assert svc in service_names, f"Service {svc} not found"
        except ApiException as e:
            pytest.fail(f"Failed to check services: {e}")

    def test_pods_healthy(self):
        """Test if all pods are in Running state."""
        try:
            pods = self.v1.list_namespaced_pod(self.namespace)
            for pod in pods.items:
                assert pod.status.phase == "Running", \
                    f"Pod {pod.metadata.name} not running. Status: {pod.status.phase}"
                
                # Check container statuses
                for container in pod.status.container_statuses:
                    assert container.ready, \
                        f"Container {container.name} in pod {pod.metadata.name} not ready"
        except ApiException as e:
            pytest.fail(f"Failed to check pods: {e}")

    def test_resource_limits(self):
        """Test if resource limits are properly set."""
        try:
            pods = self.v1.list_namespaced_pod(self.namespace)
            for pod in pods.items:
                for container in pod.spec.containers:
                    assert container.resources.limits, \
                        f"Container {container.name} in pod {pod.metadata.name} has no resource limits"
                    assert container.resources.requests, \
                        f"Container {container.name} in pod {pod.metadata.name} has no resource requests"
        except ApiException as e:
            pytest.fail(f"Failed to check resource limits: {e}")

    def test_ingress_configuration(self):
        """Test if ingress is properly configured."""
        networking_v1 = client.NetworkingV1Api()
        
        try:
            ingresses = networking_v1.list_namespaced_ingress(self.namespace)
            assert len(ingresses.items) > 0, "No ingress found"
            
            ingress = ingresses.items[0]
            assert ingress.spec.rules, "No ingress rules configured"
            assert ingress.spec.tls, "TLS not configured for ingress"
        except ApiException as e:
            pytest.fail(f"Failed to check ingress: {e}")
