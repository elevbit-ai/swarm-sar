"""A MAVLink/PX4 actuation backend.

This adapter sends velocity setpoints to a MAVLink autopilot (PX4 or ArduPilot,
real or SITL) and refreshes the drone's local state from its telemetry stream.
``pymavlink`` is an optional dependency; install it with::

    pip install "swarmsar[mavlink]"

The class imports ``pymavlink`` lazily, so the rest of the framework — and the
pure-simulation path — never requires it. Velocity is sent in the body/local
NED frame via ``SET_POSITION_TARGET_LOCAL_NED`` with only the velocity fields
unmasked, which both PX4 and ArduPilot honour in guided/offboard modes.
"""

from __future__ import annotations

from ..core.drone import Drone, DroneStatus
from ..core.vector import Vec3


class MavlinkActuator:
    """Bridge a swarm drone to a MAVLink autopilot.

    Parameters
    ----------
    connection_string:
        Anything ``mavutil.mavlink_connection`` accepts, e.g.
        ``"udpin:0.0.0.0:14540"`` (PX4 SITL) or ``"/dev/ttyACM0"``.
    source_system:
        MAVLink system id to address (one autopilot per drone).
    """

    def __init__(self, connection_string: str, source_system: int = 1) -> None:
        self.connection_string = connection_string
        self.source_system = source_system
        self._conn = None  # lazily created pymavlink connection

    # -- connection lifecycle ---------------------------------------------

    def connect(self) -> None:
        try:
            from pymavlink import mavutil
        except ImportError as exc:  # pragma: no cover - exercised only w/o extra
            raise ImportError(
                "MavlinkActuator requires pymavlink. "
                'Install it with: pip install "swarmsar[mavlink]"'
            ) from exc
        self._conn = mavutil.mavlink_connection(
            self.connection_string, source_system=self.source_system
        )
        self._conn.wait_heartbeat()

    def close(self) -> None:  # pragma: no cover - hardware/SITL only
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    # -- actuator interface ------------------------------------------------

    def apply(self, drone: Drone, desired_velocity: Vec3, dt: float) -> None:  # pragma: no cover
        """Send a velocity setpoint and refresh ``drone`` from telemetry.

        ENU (this framework) maps to MAVLink local NED as
        ``north = y, east = x, down = -z``.
        """
        if self._conn is None:
            self.connect()
        vel = desired_velocity.clamped(drone.max_speed)
        self._send_velocity_ned(north=vel.y, east=vel.x, down=-vel.z)
        self._refresh(drone)

    def _send_velocity_ned(self, north: float, east: float, down: float) -> None:
        from pymavlink import mavutil

        # Type mask: enable velocity only (bits for pos/accel/yaw set = ignore).
        type_mask = 0b0000_11_111_000_111
        self._conn.mav.set_position_target_local_ned_send(
            0,  # time_boot_ms
            self._conn.target_system,
            self._conn.target_component,
            mavutil.mavlink.MAV_FRAME_LOCAL_NED,
            type_mask,
            0.0, 0.0, 0.0,          # x, y, z position (ignored)
            north, east, down,      # vx, vy, vz velocity
            0.0, 0.0, 0.0,          # ax, ay, az (ignored)
            0.0, 0.0,               # yaw, yaw_rate (ignored)
        )

    def _refresh(self, drone: Drone) -> None:  # pragma: no cover
        msg = self._conn.recv_match(type="LOCAL_POSITION_NED", blocking=False)
        if msg is not None:
            # NED -> ENU: east=y_ned, north=x_ned, up=-z_ned.
            drone.position = Vec3(msg.y, msg.x, -msg.z)
            drone.velocity = Vec3(msg.vy, msg.vx, -msg.vz)
        batt = self._conn.recv_match(type="SYS_STATUS", blocking=False)
        if batt is not None and batt.battery_remaining >= 0:
            drone.battery = batt.battery_remaining / 100.0
        if drone.battery <= 0.0:
            drone.status = DroneStatus.LOST
