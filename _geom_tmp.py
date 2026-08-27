import struct,json,math

RAW=open('out/reference-after/braven_mpfb_reference_catch.glb','rb').read()
off=12; chunks={}
while off<len(RAW):
    clen,ctype=struct.unpack_from('<II',RAW,off); off+=8
    chunks[ctype]=RAW[off:off+clen]; off+=clen
J=json.loads(chunks[0x4E4F534A].decode('utf-8')); BIN=chunks[0x004E4942]
nodes=J['nodes']; name={i:n.get('name') for i,n in enumerate(nodes)}; IDX={v:k for k,v in name.items()}
CT={5120:('b',1),5121:('B',1),5122:('h',2),5123:('H',2),5125:('I',4),5126:('f',4)}
NC={'SCALAR':1,'VEC2':2,'VEC3':3,'VEC4':4,'MAT4':16}
def acc(ai):
    a=J['accessors'][ai]; bv=J['bufferViews'][a['bufferView']]
    fmt,sz=CT[a['componentType']]; n=NC[a['type']]
    base=bv.get('byteOffset',0)+a.get('byteOffset',0); stride=bv.get('byteStride') or sz*n
    return [struct.unpack_from('<'+fmt*n,BIN,base+i*stride) for i in range(a['count'])]
PARENT={}
for i,n in enumerate(nodes):
    for c in n.get('children',[]): PARENT[c]=i
def build(anim_override):
    cache={}
    def mat(i):
        n=nodes[i]; o=anim_override.get(i,{})
        if 'matrix' in n and i not in anim_override:
            m=n['matrix']; return [[m[0],m[4],m[8],m[12]],[m[1],m[5],m[9],m[13]],[m[2],m[6],m[10],m[14]],[m[3],m[7],m[11],m[15]]]
        t=list(o.get('translation', n.get('translation',[0,0,0])))
        r=list(o.get('rotation', n.get('rotation',[0,0,0,1])))
        s=list(o.get('scale', n.get('scale',[1,1,1])))
        x,y,z,w=r
        R=[[1-2*(y*y+z*z),2*(x*y-z*w),2*(x*z+y*w)],[2*(x*y+z*w),1-2*(x*x+z*z),2*(y*z-x*w)],[2*(x*z-y*w),2*(y*z+x*w),1-2*(x*x+y*y)]]
        return [[R[a][k]*s[k] for k in range(3)]+[t[a]] for a in range(3)]+[[0,0,0,1]]
    def mul(A,B): return [[sum(A[a][k]*B[k][q] for k in range(4)) for q in range(4)] for a in range(4)]
    def world(i):
        if i in cache: return cache[i]
        M=mat(i)
        if i in PARENT: M=mul(world(PARENT[i]),M)
        cache[i]=M; return M
    def P(nm):
        M=world(IDX[nm]); return (M[0][3],-M[2][3],M[1][3])   # gltf -> blender
    return P
REST=build({})
anim=J['animations'][0]; ov={}
for ch in anim['channels']:
    s=anim['samplers'][ch['sampler']]; out=acc(s['output'])
    ov.setdefault(ch['target']['node'],{})[ch['target']['path']]=out[0]
POSED=build(ov)

def sub(a,b): return tuple(x-y for x,y in zip(a,b))
def add(a,b): return tuple(x+y for x,y in zip(a,b))
def mulv(a,s): return tuple(x*s for x in a)
def ln(a): return math.sqrt(sum(x*x for x in a))
def dot(a,b): return sum(x*y for x,y in zip(a,b))
def cross(a,b): return (a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0])
def nrm(a):
    l=ln(a); return tuple(x/l for x in a)
DIGITS=('thumb','index','middle','ring','pinky')
# distal skin overhang past head_03, measured from the skinned mesh
TIP={'index':0.0257,'middle':0.0247,'ring':0.0260,'pinky':0.0196,'thumb':0.0274}
PAD={'index':0.0110,'middle':0.0109,'ring':0.0104,'pinky':0.0084,'thumb':0.0135}
SPLAY={'index':0.28,'middle':0.08,'ring':-0.08,'pinky':-0.22}
CURL={'thumb':(6.0,8.0),'index':(8.0,12.0),'middle':(8.0,12.0),'ring':(8.0,12.0),'pinky':(8.0,12.0)}
