import os
import pickle
from typing import List
from scipy.optimize import linear_sum_assignment


import numpy as np
import logging

import constants

ANGLE = 33
STARTING_POS = 0.7

def sorted_assignment(R, V):
    assignment = []  
    # list of indices of polygons sorted by area
    polygon_indices = list(np.argsort(V))

    # remove the last piece from the list of polygons
    if len(R) == 1:
        polygon_indices.remove(0)
    elif len(V) > 1:
        last_piece_idx = len(V) // 2
        polygon_indices.remove(last_piece_idx)

    # list of indices of requests sorted by area in ascending order
    request_indices = list(np.argsort(np.argsort(R)))

    # Assign polygons to requests by area in ascending order
    for request_idx in request_indices:
        assignment.append(int(polygon_indices[request_idx]))
    return assignment
    
def optimal_assignment(R, V):
    num_requests = len(R)
    num_values = len(V)
    
    cost_matrix = np.zeros((num_requests, num_values))
    
    # Fill the cost matrix with relative differences
    for i, r in enumerate(R):
        for j, v in enumerate(V):
            cost_matrix[i][j] = abs(r - v) / r

    # Solving the assignment problem
    row_indices, col_indices = linear_sum_assignment(cost_matrix)
    
    # Assignment array where assignment[i] is the index of V matched to R[i]
    assignment = [int(col_indices[i]) for i in range(num_requests)]
    
    return assignment

class Player:
    def __init__(self, rng: np.random.Generator, logger: logging.Logger,
                 precomp_dir: str, tolerance: int) -> None:
        """Initialise the player with the basic information

            Args:
                rng (np.random.Generator): numpy random number generator, use this for same player behavior across run
                logger (logging.Logger): logger use this like logger.info("message")
                precomp_dir (str): Directory path to store/load pre-computation
                tolerance (int): tolerance for the cake distribution
                cake_len (int): Length of the smaller side of the cake
        """

        # precomp_path = os.path.join(precomp_dir, "{}.pkl".format(map_path))

        # # precompute check
        # if os.path.isfile(precomp_path):
        #     # Getting back the objects:
        #     with open(precomp_path, "rb") as f:
        #         self.obj0, self.obj1, self.obj2 = pickle.load(f)
        # else:
        #     # Compute objects to store
        #     self.obj0, self.obj1, self.obj2 = _

        #     # Dump the objects
        #     with open(precomp_path, 'wb') as f:
        #         pickle.dump([self.obj0, self.obj1, self.obj2], f)

        self.rng = rng
        self.logger = logger
        self.tolerance = tolerance
        self.cake_len = None
        self.EASY_LEN_BOUND = 23.507
        self.num_requests_cut = 0
        self.knife_pos = []
    

    def get_starting_pos(self, requests):
        area = sum(requests) * 1.05
        h = np.sqrt(area / 1.6)
        w = h * 1.6
        return [0, round(h * STARTING_POS, 2)]

    def distance_to_edge(self, cur_pos, cake_width, cake_len):
        x, y = cur_pos
        dx = (cake_width - x) if np.cos(self.angle) > 0 else x
        dy = (cake_len - y) if np.sin(self.angle) > 0 else y
        return min(dx / abs(np.cos(self.angle)), dy / abs(np.sin(self.angle)))

    


    def move(self, current_percept) -> (int, List[int]):
        """Function which returns an action.

            Args:
                current_percept(PieceOfCakeState): contains current cake state information
            Returns:
                a tuple of format ([action=1,2,3], [list])
                if action = 1: list is [0,0]
                if action = 2: list is [x, y] (coordinates for knife position after cut)
                if action = 3: list is [p1, p2, ..., pl] (the order of polygon assignment)

        """
        polygons = current_percept.polygons
        turn_number = current_percept.turn_number
        cur_pos = current_percept.cur_pos
        requests = current_percept.requests
        cake_len = current_percept.cake_len
        cake_width = current_percept.cake_width


        ####################
        # CUTTING STRATEGY #
        ####################

        # sort requests by area in ascending order
        requests = sorted(requests)
        num_requests = len(requests)
        cake_area = cake_len * cake_width
        
        pair_sum_requests = find_similar_pair_sums(requests, cake_area)
        slice_pairs = True if cake_len > self.EASY_LEN_BOUND and cake_len <= 2* self.EASY_LEN_BOUND else False

        '''[CASE] Only one request.'''
        if num_requests == 1:
            if turn_number == 1:
                return constants.INIT, [0,0]
            elif self.num_requests_cut < num_requests:
                extra_area = 0.05 * requests[0]     # slice off the extra 5%
                extra_base = round(2 * extra_area / cake_len, 2)
                self.num_requests_cut += 1
                return constants.CUT, [extra_base, cake_len]

        '''[CASE] Simple zig-zag method.'''
        if cake_len <= self.EASY_LEN_BOUND:
            # initialize starting knife position
            if turn_number == 1:
                self.knife_pos.append([0,0])
                return constants.INIT, [0,0]
                
            if self.num_requests_cut < num_requests:
                # compute size of base from current polygon area
                curr_polygon_area = requests[self.num_requests_cut]
                curr_polygon_base = round(2 * curr_polygon_area / cake_len, 2)

                if cur_pos[1] == 0:
                    # knife is currently on the top cake edge
                    if turn_number == 2:
                        next_knife_pos = [curr_polygon_base, cake_len]
                    else:
                        next_x = round(self.knife_pos[-2][0] + curr_polygon_base, 2)
                        next_y = cake_len
                        # when knife goes over the cake width
                        if next_x > cake_width:
                            next_x = cake_width
                            next_y = round(2 * cake_area * 0.05 / (cake_width - self.knife_pos[-2][0]), 2)
                        next_knife_pos = [next_x, next_y]

                    self.knife_pos.append(next_knife_pos)
                    self.num_requests_cut += 1
                    return constants.CUT, next_knife_pos
                else:
                    # knife is currently on the bottom cake edge
                    next_x = round(self.knife_pos[-2][0] + curr_polygon_base, 2)
                    next_y = 0
                    # when knife goes over the cake width
                    if next_x > cake_width:
                        next_x = cake_width
                        next_y = cake_len - round(2 * cake_area * 0.05 / (cake_width - self.knife_pos[-2][0]), 2)
                    next_knife_pos = [next_x, next_y]
                    self.knife_pos.append(next_knife_pos)
                    self.num_requests_cut += 1
                    return constants.CUT, next_knife_pos
        elif slice_pairs:
            '''[CASE] Splitting Pairwise Triangles.'''
            # initialize starting knife position
            if turn_number == 1:
                self.knife_pos.append([0,0])
                return constants.INIT, [0,0]
            
            if num_requests % 2 == 1:
                num_requests += 1   # accounting for the fake request added

            if self.num_requests_cut < (num_requests / 2):
                # compute size of base from current polygon area
                curr_polygon_area = pair_sum_requests[self.num_requests_cut]
                curr_polygon_base = round(2 * curr_polygon_area / cake_len, 2)

                if cur_pos[1] == 0:
                    # knife is currently on the top cake edge
                    if turn_number == 2:
                        next_knife_pos = [curr_polygon_base, cake_len]
                    else:
                        next_x = round(self.knife_pos[-2][0] + curr_polygon_base, 2)
                        next_y = cake_len
                        # when knife goes over the cake width
                        if next_x > cake_width:
                            next_x = cake_width
                            next_y = round(2 * cake_area * 0.05 / (cake_width - self.knife_pos[-2][0]), 2)
                        next_knife_pos = [next_x, next_y]

                    self.knife_pos.append(next_knife_pos)
                    self.num_requests_cut += 1
                    return constants.CUT, next_knife_pos
                else:
                    # knife is currently on the bottom cake edge
                    next_x = round(self.knife_pos[-2][0] + curr_polygon_base, 2)
                    next_y = 0
                    # when knife goes over the cake width
                    if next_x > cake_width:
                        next_x = cake_width
                        next_y = round(cake_len - (2 * cake_area * 0.05 / (cake_width - self.knife_pos[-2][0])), 2)
                    next_knife_pos = [next_x, next_y]
                    self.knife_pos.append(next_knife_pos)
                    self.num_requests_cut += 1
                    return constants.CUT, next_knife_pos
            elif self.num_requests_cut >= (num_requests / 2):
                # make the horizontal dividing cut
                if (self.num_requests_cut == (num_requests / 2)):
                    # crumb cut to nearest horizontal edge
                    if cur_pos[0] == cake_width:
                        # knife is currently on the right edge of the cake
                        if (cur_pos[1] < (cake_len - cur_pos[1])):
                            next_x = round(cake_width - 0.01, 2)
                            next_y = 0
                        else:
                            next_x = round(cake_width - 0.01, 2)
                            next_y = cake_len
                        next_knife_pos = [next_x, next_y]
                        self.knife_pos.append(next_knife_pos)
                        self.num_requests_cut += 1
                        return constants.CUT, next_knife_pos
                elif (self.num_requests_cut - (num_requests / 2) == 1):
                    # cut to the horizontal cutting starting position
                    next_x = cake_width
                    next_y = round((1-0.5) * cake_len, 2)           ### starting position needs tweaking
                    next_knife_pos = [next_x, next_y]
                    self.knife_pos.append(next_knife_pos)
                    self.num_requests_cut += 1
                    return constants.CUT, next_knife_pos
                elif (self.num_requests_cut - (num_requests / 2) == 2):
                    # cut to the horizontal cutting ending position
                    next_x = 0
                    next_y = round(0.5 * cake_len, 2)               ### ending position needs tweaking
                    next_knife_pos = [next_x, next_y]
                    self.knife_pos.append(next_knife_pos)
                    self.num_requests_cut += 1
                    return constants.CUT, next_knife_pos
        else:
            '''[CASE] Rhombus Cutting.'''
            if turn_number == 1:
                self.angle = np.radians(ANGLE)
                starting_pos = self.get_starting_pos(requests)
                self.knife_pos.append(starting_pos)
                return constants.INIT, starting_pos
                
            if self.num_requests_cut < num_requests:
                x, y = cur_pos
                distance = self.distance_to_edge(cur_pos, cake_width, cake_len)
                x += np.cos(self.angle) * distance
                y += np.sin(self.angle) * distance

                # Check for boundary collisions and adjust angle
                # Left
                if x <= 0:  
                    self.angle = np.pi - self.angle
                # Right
                elif x >= cake_width:
                    self.angle = np.pi - self.angle
                # Bottom
                elif y <= 0:  
                    self.angle = -self.angle
                # Top
                elif y >= cake_len:
                    self.angle = -self.angle
                
                next_knife_pos = [round(x, 2), round(y, 2)]
                self.knife_pos.append(next_knife_pos)
                self.num_requests_cut += 1
                return constants.CUT, next_knife_pos


        #######################
        # ASSIGNMENT STRATEGY #
        #######################
        V = [p.area for p in polygons]
        assignment = optimal_assignment(current_percept.requests, V)
        
        return constants.ASSIGN, assignment
    
    
    
def find_similar_pair_sums(requests, cake_area):
    # Initialize a list to store the pairwise sums
    pair_sums = []

    # If there are an odd number of requests, add a fake request
    if len(requests) % 2 == 1:
        fake_request = cake_area * 0.05
        requests.append(fake_request)
        requests = sorted(requests)

    # Pair consecutive numbers and calculate their sums
    for i in range(0, len(requests), 2):
        pair_sum = requests[i] + requests[i + 1]
        pair_sums.append(pair_sum)

    return pair_sums
