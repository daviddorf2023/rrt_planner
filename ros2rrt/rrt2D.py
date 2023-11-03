import rclpy
from rclpy.node import Node
from visualization_msgs.msg import Marker, MarkerArray
from geometry_msgs.msg import PoseStamped
from nav_msgs.msg import Path, OccupancyGrid
import numpy as np
import matplotlib.pyplot as plt
from .submodules.TreeNode import TreeNode
from .submodules.Obstacles import Circle, Rectangle


class RRT2DNode(Node):
    """
    Generates a 2D RRT path and publishes it as a Path message and as a set of markers

    Attributes
    ----------
    start_position : np.array
        The starting position of the RRT
    goal_position : np.array
        The goal position of the RRT
    map_size : np.array
        The size of the map
    node_limit : int
        The maximum number of nodes to generate
    goal_tolerance : float
        The maximum distance between the goal and the final node
    step_size : float
        The step size for each node
    animate : bool
        Whether or not to animate the RRT

    Methods
    -------
    run_rrt_2D()
        Generates the RRT
    create_marker()
        Creates a marker for visualization
    publish_markers()
        Publishes the markers
    publish_path()
        Publishes the path
    plot_rrt_2D()
        Plots the RRT
    """

    def __init__(self):
        super().__init__('rrt_2d_node')
        self.start_position = np.array([0., 0.])
        self.goal_position = np.array([3.2, -4.1])
        self.map_size = np.array([10, 10])
        self.node_limit = 1000
        self.goal_tolerance = 0.5
        self.step_size = 0.2
        self.animate = True
        self.obstacle_1 = Circle(1.0, 1.0, 1.0)
        self.obstacle_2 = Rectangle(-1.0, -1.0, 1.0, 1.0, 0.0)
        self.obstacle_list = [self.obstacle_1, self.obstacle_2]
        self.subscribed_map = None
        self.occupancy_grid_subscription = self.create_subscription(
            OccupancyGrid, 'occupancy_grid_topic', self.occupancy_grid_callback, 10)
        self.run_rrt_2D()

    def run_rrt_2D(self):
        """
        Generates the RRT
        """
        start_node = TreeNode(self.start_position, None)
        node_list = [start_node]
        completed = False

        while len(node_list) < self.node_limit:
            random_position_x = np.random.randint(
                -self.map_size[0], self.map_size[0])
            random_position_y = np.random.randint(
                -self.map_size[1], self.map_size[1])
            random_position = np.array([random_position_x, random_position_y])
            min_distance = np.inf
            min_node = None
            for node in node_list:
                goal_vec = self.goal_position - node.val
                goal_distance = np.linalg.norm(goal_vec)
                goal_node = TreeNode(self.goal_position, node)
                if goal_distance < self.goal_tolerance:
                    node.add_child(goal_node)
                    node_list.append(goal_node)
                    completed = True
                    break
                new_node_vec = random_position - node.val  # Find node closest to random point
                distance = np.linalg.norm(new_node_vec)
                if distance < min_distance:
                    min_node_vec = new_node_vec
                    min_node = node
                min_distance = np.min([distance, min_distance])
            if completed:
                break
            if min_distance != 0:
                new_node_unit_vec = min_node_vec / min_distance
                new_node_val = min_node.val + new_node_unit_vec * self.step_size
                new_node = TreeNode(new_node_val, min_node)
                collision = False  # Check if new_node collides with any obstacles
                for obstacle in self.obstacle_list:
                    if isinstance(obstacle, Circle):
                        obstacle_vec = new_node.val - \
                            np.array([obstacle.x, obstacle.y])
                        obstacle_distance = np.linalg.norm(obstacle_vec)
                        if obstacle_distance < obstacle.radius:
                            collision = True
                            break
                    elif isinstance(obstacle, Rectangle):
                        if (obstacle.x - obstacle.width/2 < new_node.val[0] < obstacle.x + obstacle.width/2) and (obstacle.y - obstacle.height/2 < new_node.val[1] < obstacle.y + obstacle.height/2):
                            collision = True
                            break
                if collision:
                    continue
                min_node.add_child(new_node)
                node_list.append(new_node)

        if not completed:
            self.get_logger().info('Path not found')
            return

        self.publish_markers(node_list)
        self.publish_path(node_list)
        self.plot_rrt_2D(node_list)

    def occupancy_grid_callback(self, msg):
        """
        Callback for the OccupancyGrid subscriber.

        Parameters:
        - msg (OccupancyGrid): The received OccupancyGrid message.
        """
        self.map_data = msg.data

    def create_marker(self, marker_type: int, marker_id: int, color: list, scale: list, position: list) -> Marker:
        """
        Creates a marker for visualization.

        Parameters
        ----------
        marker_type : int
            The type of marker
        marker_id : int
            The ID of the marker
        color : list
            The color of the marker
        scale : list
            The scale of the marker
        position : list
            The position of the marker
        """
        marker = Marker()
        marker.header.frame_id = "map"
        marker.ns = "rrt_markers"
        marker.id = marker_id
        marker.type = marker_type
        marker.action = Marker.ADD
        marker.scale.x = scale[0]
        marker.scale.y = scale[1]
        marker.scale.z = scale[2]
        marker.color.r = color[0]
        marker.color.g = color[1]
        marker.color.b = color[2]
        marker.color.a = color[3]
        marker.pose.position.x = position[0]
        marker.pose.position.y = position[1]
        marker.pose.position.z = position[2]
        return marker

    def publish_markers(self, node_list: list):
        """
        Publishes the markers

        Parameters
        ----------
        node_list : list
            The list of nodes in the RRT
        """
        marker_publisher = self.create_publisher(
            MarkerArray, 'rrt_markers', 10)
        marker_array = MarkerArray()

        # Create markers for the RRT nodes and connections
        for node in node_list:
            marker = self.create_marker(Marker.SPHERE, node_list.index(node) + 2, [
                0.0, 1.0, 0.0, 1.0], [0.1, 0.1, 0.1], [node.val[0], node.val[1], 0.0])
            marker_array.markers.append(marker)
        # Create markers for the obstacles
        for obstacle in self.obstacle_list:
            if isinstance(obstacle, Circle):
                marker = self.create_marker(Marker.CYLINDER, self.obstacle_list.index(
                    obstacle) + len(node_list) + 2, [1.0, 0.0, 0.0, 1.0], [obstacle.radius * 2, obstacle.radius * 2, 0.1], [obstacle.x, obstacle.y, 0.0])
                marker_array.markers.append(marker)
            elif isinstance(obstacle, Rectangle):
                marker = self.create_marker(Marker.CUBE, self.obstacle_list.index(
                    obstacle) + len(node_list) + 2, [1.0, 0.0, 0.0, 1.0], [obstacle.width, obstacle.height, 0.1], [obstacle.x, obstacle.y, 0.0])
                marker_array.markers.append(marker)
        marker_publisher.publish(marker_array)

    def publish_path(self, node_list: list):
        """
        Publishes the path

        Parameters
        ----------
        node_list : list
            The list of nodes in the RRT
        """
        path_publisher = self.create_publisher(Path, 'rrt_path', 10)
        path = Path()
        path.header.frame_id = "map"
        current_node = node_list[-1]
        while current_node.parent:
            pose = PoseStamped()
            pose.header.frame_id = "map"
            pose.header.stamp = self.get_clock().now().to_msg()
            pose.pose.position.x = current_node.val[0]
            pose.pose.position.y = current_node.val[1]
            pose.pose.position.z = 0.0
            path.poses.append(pose)
            current_node = current_node.parent
        path_publisher.publish(path)

    def plot_rrt_2D(self, node_list):
        """
        Plots the RRT

        Parameters
        ----------
        node_list : list
            The list of nodes in the RRT
        """
        plt.xlim(-self.map_size[0], self.map_size[0])
        plt.ylim(-self.map_size[1], self.map_size[1])
        plt.scatter(self.start_position[0], self.start_position[1], c='r')
        plt.scatter(self.goal_position[0], self.goal_position[1], c='b')
        if self.animate:
            plt.ion()
        for node in node_list:
            if node.parent:
                plt.plot([node.val[0], node.parent.val[0]],
                         [node.val[1], node.parent.val[1]],
                         'g')
                if self.animate:
                    plt.pause(0.05)
        current_node = node_list[-1]
        while current_node.parent:
            if current_node.parent:
                plt.plot([current_node.val[0], current_node.parent.val[0]],
                         [current_node.val[1], current_node.parent.val[1]],
                         c='r')
                if self.animate:
                    plt.pause(0.0001)
            current_node = current_node.parent
        if self.animate:
            plt.ioff()
        plt.show()


def main(args=None):
    rclpy.init(args=args)
    rrt_2d_node = RRT2DNode()
    rclpy.spin(rrt_2d_node)
    rrt_2d_node.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()
