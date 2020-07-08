INPPATH = 'C:/Temp/123117Kartchnerv3_box_c3d4.inp'
ODBPATH = 'C:/Temp/123117Kartchnerv3_box_c3d4.odb'
OUTPATH = 'C:/Temp/123117Kartchnerv3_box_c3d4.vtu'

from odbAccess import openOdb
from abaqusConstants import *


class DataSet:
    def __init__(self):
        self.nodes = {}
        self.elements = {}
        self.stress = {}
        self.displacement = {}

    def insertNode(self, nid, x, y, z):
        self.nodes[int(nid)] = [float(x), float(y), float(z)]

    def insertTetr(self, eid, n0, n1, n2, n3):
        self.elements[int(eid)] = [int(n0), int(n1), int(n2), int(n3)]
        
    def insertStress(self, eid, mises, s11, s22, s33, s12, s13, s23):
        self.stress[int(eid)] = [float(mises), float(s11), float(s22), float(s33), float(s12), float(s13), float(s23)]

    def insertDisplacement(self, nid, ux, uy, uz):
        self.displacement[int(nid)] = [float(ux),  float(uy),  float(uz)]

    def save(self, file_name):
        nids = sorted(self.nodes.keys())
        eids = sorted(self.elements.keys())
        with open(file_name, 'w') as ofs:
            ofs.write('<?xml version="1.0"?>')
            ofs.write('<VTKFile type="UnstructuredGrid" version="0.1" byte_order="LittleEndian" header_type="UInt32">')
            ofs.write('<UnstructuredGrid>')
            ofs.write('<Piece NumberOfPoints="%d" NumberOfCells="%d" >' % (len(self.nodes), len(self.elements)))
            ofs.write('<Points>')
            ofs.write('<DataArray type="Float32" Name="Points" NumberOfComponents="3" format="ascii">')
            for key in nids:
                x, y, z = self.nodes[key]
                ofs.write("%f %f %f " % (x, y, z))
            ofs.write('</DataArray>')
            ofs.write('</Points>')
            ofs.write('<PointData Vectors="displacement">')
            ofs.write('<DataArray type="Float32" NumberOfComponents="3" format="ascii" Name="displacement">')
            for key in nids:
                ux, uy, uz = self.displacement[key]
                ofs.write("%f %f %f " % (ux, uy, uz))
            ofs.write('</DataArray>')
            ofs.write('</PointData>')
            ofs.write('<Cells>')
            ofs.write('<DataArray type="Int64" Name="connectivity" format="ascii">')
            for key in eids:
                ns = self.elements[key]
                nns = map(lambda x: str(x - 1), ns)
                cons = " ".join(nns)
                ofs.write(cons + ' ')
            ofs.write('</DataArray>')
            ofs.write('<DataArray type="Int64" Name="offsets" format="ascii">')
            for key in eids:
                ofs.write("%d " % (key * 4))
            ofs.write('</DataArray>')
            ofs.write('<DataArray type="UInt8" Name="types" format="ascii">')
            for key in eids:
                ofs.write("10 ")
            ofs.write('</DataArray>')
            ofs.write('</Cells>')
            ofs.write('<CellData Scalars="Mises" Tensors="Stress">')
            ofs.write('<DataArray type="Float32" Name="Mises" NumberOfComponents="1" format="ascii" >')
            for key in eids:
                ofs.write("%f " % self.stress[key][0])
            ofs.write('</DataArray>')
            ofs.write('<DataArray type="Float32" Name="Stress" NumberOfComponents="9" format="ascii">')
            for key in eids:
                s11, s22, s33, s12, s13, s23 = self.stress[key][1:]
                ofs.write("%f %f %f %f %f %f %f %f %f " % (s11, s12, s13, s12, s22, s23, s13, s23, s33))
            ofs.write('</DataArray>')
            ofs.write('</CellData>')
            ofs.write('</Piece>')
            ofs.write('</UnstructuredGrid>')
            ofs.write('</VTKFile>')
            ofs.close()


data = DataSet()
# 0 - nothing
# 1 - node
# 2 - tetrahedron
state = 0
# read input file
with open(INPPATH, 'r') as input_file:
    for line in input_file:
        if line.strip() == '*Node':
            state = 1
        elif line.startswith('*Element, type=C3D4'):
            state = 2
        else:
            if line.startswith("*") and (not line.startswith("**")):
                state = 0
            elif state == 1:
                uid, x, y, z = line.strip().split(',')
                data.insertNode(uid, x, y, z)
            elif state == 2:
                el, n0, n1, n2, n3 = line.strip().split(',')
                data.insertTetr(el, n0, n1, n2, n3)
            else:
                pass

# Open the odb
myOdb = openOdb(ODBPATH)

# Get the frame repository for the step, find number of frames (starts at frame 0)
stepName = myOdb.steps.keys()[0]
frames = myOdb.steps[stepName].frames
numFrames = len(frames)

# Isolate the instance, get the number of nodes and elements
instanceName = myOdb.rootAssembly.instances.keys()[0]
myInstance = myOdb.rootAssembly.instances[instanceName]
numNodes = len(myInstance.nodes)
numElements = len(myInstance.elements)
# print("num El %d, num Nodes %d" % (numElements, numNodes))

strss = myOdb.steps[stepName].frames[-1].fieldOutputs['S'].getSubset(position=CENTROID)
disps = myOdb.steps[stepName].frames[-1].fieldOutputs['U']
# print("strss: %d displacement: %d" % (len(strss.values), len(disps.values)))

for srs in strss.values:
    eid = srs.elementLabel
    mises = srs.mises
    sxx = srs.data[0]
    syy = srs.data[1]
    szz = srs.data[2]
    sxy = srs.data[3]
    sxz = srs.data[4]
    syz = srs.data[5]
    # print("element: %d >>> s11 %f s22 %f s33 %f s12 %f s13 %f s23 %f" %
    #       (eid, sxx, syy, szz, sxy, sxz, syz))
    data.insertStress(eid, float(mises), float(sxx), float(syy), float(szz), float(sxy), float(sxz), float(syz))

for disp in disps.values:
    nid = disp.nodeLabel
    ux = disp.data[0]
    uy = disp.data[1]
    uz = disp.data[2]
    data.insertDisplacement(nid, ux, uy, uz)

data.save(OUTPATH)
