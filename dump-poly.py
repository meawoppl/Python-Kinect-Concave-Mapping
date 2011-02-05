from pylab import *
from scipy import *
from scipy import misc
import sys
from tables import *
from sift import *

h5 = openFile( sys.argv[1] )

text_header = '''ply
format ascii 1.0
comment Auto-encoded By matts dumper
element vertex %i
property float x
property float y
property float z
element face %i
property list uchar int vertex_index
end_header
'''

# Precompute the location to depth information
width_fov_deg = 57
width_fov_rad = width_fov_deg * (pi / 180)
width_fov_rad = width_fov_rad / 2

height_fov_deg = 43
height_fov_rad = height_fov_deg * (pi / 180)
height_fov_rad = height_fov_rad / 2

# Max and min Depths
max_depth = 5                   # meters
min_depth = 0.4                 # meters (0.4?)

# l-r FOV of Kinect is 57 degrees, so
theta_bound = ((57. / 2) * (pi / 180)) # Radians
max_width   = theta_bound * max_depth
min_width   = theta_bound * min_depth

# t-b FOV of Kinect is 43 degrees, so
phi_bound   = ((43. / 2) * (pi / 180)) # Radians
max_height  = phi_bound * max_depth
min_height  = phi_bound * min_depth

xs, ys = mgrid[-1:1:480j, -1:1:640j]

mi_xs = xs * min_width
mx_xs = xs * max_width

mi_ys = ys * min_height
mx_ys = ys * max_height


def depth_to_xyz(dep):
    # Normalized depth
    n_z = (dep / 255.)

    # mi = 1 at minimum depth, 
    # mx = 1 at max depth 
    # (linear combination of these . . .)
    mx = (1. - n_z)
    mi = (n_z - 1.)

    x = (mi * mi_xs) + (mx * mx_xs)
    y = (mi * mi_ys) + (mx * mx_ys)
    z = (mi * min_depth) + (mx * max_depth)

    return x, y, z

def frame_to_ply_file(depth, filename):
    # It reports 255 when there is no signal . . . 
    # depth = ma.masked_array(depth, depth==255)

    # Mask too deep and too shallow
    depth = depth
    depth = ma.masked_array( depth, logical_or(depth == 0, depth == 255))

    # Compute the coordinates based on the depth map, and array for ply file    
    x, y, z = depth_to_xyz(depth)

    # Clip the crappy edge off
    ss = 10
    x = x[:,:-12][::ss,::ss]
    y = y[:,:-12][::ss,::ss]
    z = z[:,:-12][::ss,::ss]

    df_shape = x.shape

    # String em out and line em up
    x = x.flatten()
    y = y.flatten()
    z = z.flatten()

    # Fit meshlab convention
    xyz = c_[y, x, z]

    # Make sure all points in the group are good
    xyz_masked = (x.mask & y.mask & z.mask).squeeze()

    # Toss the cruft
    xyz = xyz[logical_not(xyz_masked), :]

    # Record the number of vertices
    num_vertex = xyz.shape[0]

    # Map the indices onto good points in 2dee
    indices = arange(num_vertex, dtype=int32)
    indices1 = ma.masked_array( zeros(df_shape, dtype=int32), xyz_masked.reshape(df_shape))

    # This assignment makes the mask of the assigned values False, 
    # so we copy then reset the mask  
    # BUG?
    msk_temp = indices1.mask.copy()

    indices1[logical_not(indices1.mask)] = indices
    indices1.mask = msk_temp
    # Mask one of the edge sets to exclude wrap-around polygons
    indices1.mask[ 0,:] = True
    indices1.mask[-1,:] = True
    indices1.mask[:, 0] = True
    indices1.mask[:,-1] = True

    indices2 = roll(indices1, -1, axis=0)
    indices3 = roll(indices1, -1, axis=1)

    indices4 = roll(indices1, 1, axis=0)
    indices5 = roll(indices1, 1, axis=1)


    indices1 = indices1.flatten()
    indices2 = indices2.flatten()
    indices3 = indices3.flatten()

    indices4 = indices4.flatten()
    indices5 = indices5.flatten()
    

    # Now lets see which of those are any good
    iii1 = c_[indices1, indices2, indices3]
    iii2 = c_[indices1, indices4, indices5]

    # TODO: more stupid checks here
    poly_has_masked_vertex1 = (indices1.mask | indices2.mask | indices3.mask).squeeze()
    poly_has_masked_vertex2 = (indices1.mask | indices4.mask | indices5.mask).squeeze()

    iii1 = iii1[logical_not(poly_has_masked_vertex1), :]
    iii2 = iii2[logical_not(poly_has_masked_vertex2), :]

    iii = r_[iii1, iii2]

    faces_on_poly = ones(iii.shape[0]) * 3
    faces = c_[faces_on_poly, iii]

    num_faces = faces.shape[0]

    print "Writing %i vertices and %i faces." % (num_vertex, num_faces)

    flo = open(filename, "w")
    flo.write(text_header % (num_vertex, num_faces) )
    savetxt(flo, xyz, fmt="%f")
    savetxt(flo, faces, fmt="%i")

    flo.close()

    return xyz, iii

def stupid_pgm(filename, datas):
    open(filename, "w").write('P5\n%i %i\n255\n%s' % (datas.shape[1], datas.shape[0], datas.T.tostring()))


def match_two_files(file1, file2):
    process_image(file1, "keys1.key")
    process_image(file2, "keys2.key")

    l1,d1 = read_features_from_file('keys1.key')
    l2,d2 = read_features_from_file('keys2.key')

    i1 = misc.imread(file1, flatten=True)
    i2 = misc.imread(file2, flatten=True)
    
    ms = match(d1, d2)

    plot_matches(i1, i2, l1, l2, ms)
    


if __name__ == "__main__":
    match_two_files("frames/frame-000.pgm", "frames/frame-045.pgm")
    1/0
    for frame_number in range(0, 299, 15):
        print "Doing frame", frame_number
        sys.stdout.flush()
        depth = h5.root.dep[:,:,frame_number]
        color = h5.root.rgb[:,:,:,frame_number]
        filename = "frames/frame-%03i.pgm" % frame_number
        stupid_pgm(filename, (color.sum(axis=2)//3)[::5,::5])    

        xyz, iii = frame_to_ply_file(depth, "ply/frame-%03i.ply" % frame_number)

        # last_image = color.copy()
        # l1, d1 = read_features_from_file('keys.key')

        # 1/0
