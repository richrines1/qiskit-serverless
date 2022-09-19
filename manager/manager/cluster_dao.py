"""Dao definition for cluster """
from subprocess import PIPE, run
import logging
from manager.errors import CommandError, NotFoundError


log = logging.getLogger("cluster_dao")


class AbstractClusterDAOFactory:
    """Factory object for ClusterDAO."""

    def create_instance(self, namespace):
        """Returns ClusterDAO instance"""


class ClusterDAOFactory(AbstractClusterDAOFactory):
    """Factory object for ClusterDAO."""

    def create_instance(self, namespace):
        """Returns ClusterDAO instance"""
        return ClusterDAO(namespace)


class ClusterDAO:
    """Cluster data access object"""

    def __init__(self, namespace: str):
        """
        Initialize cluster dao
        Args:
            namespace: namespace for ray cluster"""
        self.namespace = namespace

    @staticmethod
    def run(command):
        """
        Executes a command line instruction.
        Args:
            command: command to be executed
        Returns:
            execution output
        Raises:
            CommandError
        """
        result = run(
            command, stdout=PIPE, stderr=PIPE, universal_newlines=True, cwd="ray"
        )
        log.info(
            "Executed: %s. Got: [%s] and code [%d]. ERR: [%s]",
            command,
            result.stdout,
            result.returncode,
            result.stderr,
        )
        if result.returncode == 0:  # success
            return result.stdout
        raise CommandError(result.stderr)

    def get_all(self):
        """
        Obtains all ray clusters available in kubernetes.

        Returns:
            List of clusters
        """
        log.info("Get all clusters.")
        get_clusters_command = [
            "kubectl",
            "-n",
            self.namespace,
            "get",
            "rayclusters",
            "--no-headers",
            "-o",
            "custom-columns=NAME:metadata.name",
        ]
        result = self.run(get_clusters_command)

        clusters = []
        for line in iter(result.strip().split("\n")):
            log.debug(line)
            cluster = {"name": line}
            clusters.append(cluster)
        return clusters

    def get(self, name):
        """
        Obtains ray cluster details kubernetes.
        Args:
            name: name of the cluster
        Returns:
            Cluster details.
        Raises:
            CommandError, NotFoundError
        """
        log.info("Get details for cluster with name %s", name)
        get_clusters_command = [
            "kubectl",
            "-n",
            self.namespace,
            "get",
            "service",
            str(name) + "-ray-head",
            "-o",
            "custom-columns=IP:.spec.clusterIP,PORT:.spec.ports[0].targetPort",
            "--no-headers",
        ]
        try:
            result = self.run(get_clusters_command)
            host_port = result.strip().split()
            return {
                "name": name,
                "host": name + "-ray-head",
                "ip": host_port[0],
                "port": host_port[1],
            }
        except CommandError as err:
            if "NotFound" in str(err):
                raise NotFoundError(str(err)) from err
            raise err

    def create(self, data):
        """
        Creates a ray cluster.
        Args:
            data: payload for creating the cluster containing the name of the cluster
        Returns:
            Cluster name.
        Raises:
            CommandError
        """
        log.info("Create cluster with name %s", data["name"])
        create_cluster_command = [
            "helm",
            "-n",
            self.namespace,
            "install",
            data["name"],
            "--set",
            "clusterOnly=true",
            ".",
            "--create-namespace",
        ]
        self.run(create_cluster_command)
        cluster = {"name": data["name"]}
        return cluster

    def delete(self, name):
        """
        Deletes a ray cluster.
        Args:
            name: name of the cluster to be deleted
        Raises:
            CommandError, NotFoundError
        """
        log.info("Delete cluster with name %s", str(name))
        delete_cluster_command = [
            "kubectl",
            "-n",
            self.namespace,
            "delete",
            "rayclusters",
            name,
        ]
        try:
            self.run(delete_cluster_command)
        except CommandError as err:
            if "NotFound" in str(err):
                raise NotFoundError(str(err)) from err
            raise err
