import rclpy
from rclpy.node import Node
from visualization_msgs.msg import Marker, MarkerArray
from .submodules.Marker import Sphere, Box, create_marker


class ObstaclePublisher2D(Node):

    def __init__(self):
        super().__init__('obstacle_publisher_3D')
        self.publisher = self.create_publisher(
            MarkerArray, 'obstacle_markers_3D', 10)
        self.timer = self.create_timer(
            1.0, self.publish_obstacle)
        self.obstacle_1 = Sphere(1.0, 1.0, 1.0, 1.0)
        self.obstacle_2 = Box(-1.0, -1.0, 1.0, 1.0, 1.0, 1.0, 0.0)
        self.obstacle_list = [self.obstacle_1, self.obstacle_2]

    def publish_obstacle(self):
        marker_array = MarkerArray()
        for obstacle in self.obstacle_list:
            if isinstance(obstacle, Sphere):
                marker = create_marker(Marker.SPHERE, self.obstacle_list.index(
                    obstacle), [1.0, 0.0, 0.0, 1.0],
                    [obstacle.radius * 2, obstacle.radius * 2, obstacle.radius * 2],
                    [obstacle.x, obstacle.y, obstacle.z])
                marker_array.markers.append(marker)
            elif isinstance(obstacle, Box):
                marker = create_marker(Marker.CUBE, self.obstacle_list.index(
                    obstacle), [1.0, 0.0, 0.0, 1.0],
                    [obstacle.width, obstacle.height, obstacle.depth],
                    [obstacle.x, obstacle.y, obstacle.z])
                marker_array.markers.append(marker)
        self.publisher.publish(marker_array)


def main(args=None):
    rclpy.init(args=args)
    obstacle_publisher = ObstaclePublisher2D()
    rclpy.spin(obstacle_publisher)
    rclpy.shutdown()
