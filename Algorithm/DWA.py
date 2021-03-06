import math
import numpy as np
import matplotlib.pyplot as plt
from PID import PID
from math import cos, sin, pi
import time
import sys
sys.path.append("../../")


show_animation = True


class Config():
    # simulation parameters

    def __init__(self):
        # robot parameter
        self.max_speed = 1.0  # [m/s]
        self.min_speed = 0  # [m/s]
        self.max_yawrate = 0.65  # [rad/s]
        self.max_accel = 0.45  # [m/ss]
        self.max_dyawrate = 0.5  # 40.0 * math.pi / 180.0  # [rad/ss]
        self.v_reso = 0.01  # [m/s]
        self.yawrate_reso = 0.1 * pi / 180.0  # [rad/s]
        self.dt = 0.1  # [s]
        self.predict_time = 3.0  # [s]
        self.to_goal_cost_gain = 2.0
        self.speed_cost_gain = 1.0
        self.robot_radius = 1  # [m]



# 注意适用范围: left, right 0~1000 rpm
# left, right都为正表示前进
def simulate(state, left, right, dt):
    x = state['x']  # 北东系x坐标 [m]
    y = state['y']  # 北东系y坐标 [m]
    u0 = state['u']  # x方向速度(大地坐标系) [m/s]
    v0 = state['v']  # y方向速度(大地坐标系) [m/s]
    phi = state['phi']  # 艏向角，即船头与正北的夹角，范围为0~2PI [rad]
    r0 = state['alpha']  # 艏向角速度 [rad/s]

    left = left / 60  # 船舶左桨转速 [rps]
    right = right / 60  # 船舶右桨转速 [rps]

    u = v0 * sin(phi) + u0 * cos(phi)  # 转为随船坐标系, i.e. 船纵向速度
    v = v0 * cos(phi) - u0 * sin(phi)  # 船横向速度
    #  根据当前状态, 螺旋桨转速1500, 1500 / 0, 1500, 求du, dv, dr极值
    du = (-6.7 * u ** 2 + 15.9 * r0 ** 2 + 0.01205 * (left ** 2 + right ** 2) - 0.0644 * (
        u * (left + right) + 0.45 * r0 * (left - right)) + 58 * r0 * v) / 33.3
    dv = (-29.5 * v + 11.8 * r0 - 33.3 * r0 * u) / 58
    dr = (-0.17 * v - 2.74 * r0 - 4.78 * r0 * abs(r0) + 0.45 * (
        0.01205 * (left ** 2 - right ** 2) - 0.0644 * (
            u * (left - right) + 0.45 * r0 * (left + right)))) / 6.1
    u1 = u + du * dt
    v1 = v + dv * dt
    r = r0 + dr * dt
    phi1 = phi + (r + r0) * dt / 2
    U = u1 * cos(phi) - v1 * sin(phi)
    V = u1 * sin(phi) + v1 * cos(phi)
    X = x + (u0 + U) * dt / 2
    Y = y + (v0 + V) * dt / 2

    phi1 = phi1 % (2 * pi)

    return {
        'x': X,
        'y': Y,
        'u': U,
        'v': V,
        'phi': phi1,
        'alpha': r
    }


def simulate_model(state, dt): # left, right, dt):
    # x = state['x']
    # y = state['y']
    # u0 = state['u']
    # v0 = state['v']
    # phi = state['phi']  # 艏向角
    # r0 = state['alpha'] # 角速度
    x = state[0]
    y = state[1]
    u0 = state[3] * cos(state[2])
    v0 = state[3] * sin(state[2])
    phi = state[2]  # 艏向角
    r0 = state[4] # 角速度

    left = 800 / 60
    right = 800 / 60

    u = v0 * sin(phi) + u0 * cos(phi)
    v = v0 * cos(phi) - u0 * sin(phi)
    du = (-6.7 * u ** 2 + 15.9 * r0 ** 2 + 0.01205 * (left ** 2 + right ** 2) - 0.0644 * (
        u * (left + right) + 0.45 * r0 * (left - right)) + 58 * r0 * v) / 33.3
    dv = (-29.5 * v + 11.8 * r0 - 33.3 * r0 * u) / 58
    dr = (-0.17 * v - 2.74 * r0 - 4.78 * r0 * abs(r0) + 0.45 * (
        0.01205 * (left ** 2 - right ** 2) - 0.0644 * (
            u * (left - right) + 0.45 * r0 * (left + right)))) / 6.1
    u1 = u + du * dt
    v1 = v + dv * dt
    state[4] = r0 + dr * dt
    phi1 = phi + (state[4] + r0) * dt / 2
    U = u1 * cos(phi) - v1 * sin(phi)
    V = u1 * sin(phi) + v1 * cos(phi)
    state[3] = np.linalg.norm([U, V])
    state[0] = x + (u0 + U) * dt / 2
    state[1] = y + (v0 + V) * dt / 2

    state[2] = phi1 % (2 * pi)

    # return {
    #     'x': X,
    #     'y': Y,
    #     'u': U,
    #     'v': V,
    #     'phi': phi1,
    #     'alpha': r
    # }
    return state

kp = 800
ki = 3
kd = 10
baseline = 1000
data = []
# 这里随机生成初始状态
old_state = {
    'x': 0,
    'y': 0,
    'u': 0, # normal(0, 0.2),
    'v': 0,# normal(0, 0.2),
    # 'phi': np.random.rand() * 2 * pi,
    'phi': math.pi / 8.0,
    'alpha': 0  #normal(0, 0.01)
}


# x(m), y(m), yaw(rad), v(m/s), yaw spd(rad/s)
# u[0] v, u[1] yaw spd
def motion(x, u, dt):
    # motion model

    x[2] += u[1] * dt
    x[0] += u[0] * math.cos(x[2]) * dt
    x[1] += u[0] * math.sin(x[2]) * dt
    x[3] = u[0]
    x[4] = u[1]

    return x


def calc_dynamic_window(x, config):

    # Dynamic window from robot specification
    Vs = [config.min_speed, config.max_speed,
          -config.max_yawrate, config.max_yawrate]

    # Dynamic window from motion model
    Vd = [x[3] - config.max_accel * config.dt,
          x[3] + config.max_accel * config.dt,
          x[4] - config.max_dyawrate * config.dt,
          x[4] + config.max_dyawrate * config.dt]

    #  [vmin, vmax, yawrate min, yawrate max]
    dw = [max(Vs[0], Vd[0]), min(Vs[1], Vd[1]),
          max(Vs[2], Vd[2]), min(Vs[3], Vd[3])]

    return dw


def calc_trajectory(xinit, v, y, config):

    x = np.array(xinit)
    traj = np.array(x)
    time = 0
    while time <= config.predict_time:
        x = motion(x, [v, y], config.dt)
        #x = simulate_model(x, left, right, config.dt)
        traj = np.vstack((traj, x))
        time += config.dt
    # while (abs(x[3] - v) > 0.01) & (abs(x[2] - y) > 0.01):
    #     x = simulate_model(x, config.dt)
    #     traj = np.vstack((traj, x))

    return traj


def calc_final_input(x, u, dw, config, goal, ob):

    xinit = x[:]
    min_cost = 10000.0
    min_u = u
    min_u[0] = 0.0
    best_traj = np.array([x])

    # evaluate all trajectory with sampled input in dynamic window
    for v in np.arange(dw[0], dw[1], config.v_reso):
        for y in np.arange(dw[2], dw[3], config.yawrate_reso):
            traj = calc_trajectory(xinit, v, y, config)

            # calc cost
            to_goal_cost = calc_to_goal_cost(traj, goal, config)
            speed_cost = config.speed_cost_gain * \
                (config.max_speed - traj[-1, 3])
            ob_cost = calc_obstacle_cost(traj, ob, config)
            # print(ob_cost)

            final_cost = to_goal_cost + speed_cost + ob_cost

            #print (final_cost)

            # search minimum trajectory
            if min_cost >= final_cost:
                min_cost = final_cost
                min_u = [v, y]
                best_traj = traj
    # print('goal_cost', to_goal_cost, 'speed_cost', speed_cost, 'obstacle_cost', ob_cost)
    # print('min_u', min_u, 'best_traj', best_traj)
    return min_u, best_traj


def calc_obstacle_cost(traj, ob, config):
    # calc obstacle cost inf: collistion, 0:free

    skip_n = 2
    minr = float("inf")

    for ii in range(0, len(traj[:, 1]), skip_n):
        for i in range(len(ob[:, 0])):
            ox = ob[i, 0]
            oy = ob[i, 1]
            dx = traj[ii, 0] - ox
            dy = traj[ii, 1] - oy

            r = math.sqrt(dx**2 + dy**2)
            if r <= config.robot_radius:
                return float("Inf")  # collision

            if minr >= r:
                minr = r

    return 1.0 / minr  # OK

cnt = 0
def calc_to_goal_cost(traj, goal, config):
    # calc to goal cost. It is 2D norm.

    goal_magnitude = math.sqrt(goal[0]**2 + goal[1]**2)
    traj_magnitude = math.sqrt(traj[-1, 0]**2 + traj[-1, 1]**2)
    dot_product = (goal[0] * traj[-1, 0]) + (goal[1] * traj[-1, 1])
    error = dot_product / (goal_magnitude * traj_magnitude)
    if abs(error) > 1:
        global cnt
        cnt += 1
        print("error", error, 'count', cnt, 'goal_mag', goal_magnitude, 'traj_mag', traj_magnitude, 'division', goal_magnitude * traj_magnitude, 'dot_product', dot_product)
        error = 1 if error > 0 else -1
    error_angle = math.acos(error)
    cost = config.to_goal_cost_gain * error_angle

    return cost


def dwa_control(x, u, config, goal, ob):
    # Dynamic Window control

    dw = calc_dynamic_window(x, config)

    u, traj = calc_final_input(x, u, dw, config, goal, ob)

    return u, traj


def plot_arrow(x, y, yaw, length=0.5, width=0.1):  # pragma: no cover
    plt.arrow(x, y, length * math.cos(yaw), length * math.sin(yaw),
              head_length=width, head_width=width)
    plt.plot(x, y)


def main():
    print(__file__ + " start!!")
    # initial state [x(m), y(m), yaw(rad), v(m/s), omega(rad/s)]
    x = np.array([0.0, 0.1, math.pi / 8.0, 0.0, 0.0])
    # goal position [x(m), y(m)]
    goal = np.array([-90.0 , 5.0])
    # obstacles [x(m) y(m), ....]
    ob = np.array([[-1.0, -1.0],
                   [0.0, 2.0],
                   [-40.0, 10.0],
                   # [5.0, 4.0],
                   # [5.0, 5.0],
                   # [6.0, 7.5],
                   # [6.5, 8.5],
                   # [7.5, 9.5],
                   # [8.5, 9.5],
                   [-80.0, 2.0]
                   ])
    u = np.array([0.0, 0.0])
    config = Config()
    traj = np.array(x)

    pid = PID(kp=kp, ki=ki, kd=kd, minout=-2000, maxout=2000, sampleTime=0.1)
    state = old_state

    for i in range(1000):
        start = time.perf_counter()
        # 虚拟动态障碍物
        ob[2, 0] -= 0.03
        ob[2,1] += 0.005
        ob[0, 0] -= 0.01
        ob[3,1] += 0.005
        goal[0] -= 0.05
        goal[1] += 0.05

        x = np.array([state['x'], state['y'], state['phi'], math.sqrt(state['u'] ** 2 + state['v'] ** 2), state['alpha']])

        u, ltraj = dwa_control(x, u, config, goal, ob)
        # print(goal)
        # x = motion(x, u, config.dt)
        traj = np.vstack((traj, x))  # store state history

        old = state['phi']
        state['phi'] += u[1] * 0.3  # 这里应该乘多少?
        state['u'] = u[0] * cos(state['phi'])
        state['v'] = u[0] * sin(state['phi'])
        ideal_angle = state['phi']
        output = pid.compute(old, ideal_angle)
        print('output', output, 'ideal_angle', ideal_angle, 'real_angle', old)
        # output = 0 if abs(output) < 5 else output
        left, right = baseline + output / 2, baseline - output / 2
        left = max(min(left, 1000), -1000)
        right = max(min(right, 1000), -1000)
        print('left', left, 'right', right)
        adata = [state['x'], state['y'], state['u'], state['v'], state['phi'], state['alpha'], left, right]
        data.append(adata)
        state = simulate(state, left, right, 0.1)
        # print(traj)

        elapsed = (time.perf_counter() - start)
        print("Time used:", elapsed)

        if show_animation:
            plt.cla()
            plt.plot(ltraj[:, 0], ltraj[:, 1], "-g")
            plt.plot(x[0], x[1], "xr")
            plt.plot(goal[0], goal[1], "xb")
            plt.plot(ob[:, 0], ob[:, 1], "ok")
            plot_arrow(x[0], x[1], x[2])
            plt.axis("equal")
            plt.grid(True)
            plt.pause(0.0001)

        # check goal
        if math.sqrt((x[0] - goal[0])**2 + (x[1] - goal[1])**2) <= config.robot_radius:
            print("Goal!!")
            break

    print("Done")
    if show_animation:
        plt.plot(traj[:, 0], traj[:, 1], "-r")
        plt.pause(0.0001)

    plt.show()

if __name__ == '__main__':
    main()
