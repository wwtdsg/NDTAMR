"""
    The NDTree module contains the n-dimensional tree structure
    and routines for creating trees and integrating trees. 
"""
from __future__ import print_function, division
import numpy as np
from .Data import Empty

"""These are some example prolongation/restriction operators"""
def prolongate_injection(n):
    """Copy data to each child."""
    if n.data is not None:
        for c in n.child:
            n.data = n.data.copy()
    n.data = None

def restrict_injection(n):
    """Take the first child's data."""
    if n.child[0].data is not None:
        n.data = n.child[0].data.copy()
    
def prolongate_average(n):
    """Evenly distribute the data to the children."""
    if n.data is not none:
        for c in n.child:
            n.data = n.data / self.nchildren
    n.data = None
def restrict_average(n):
    """Add up the children's data."""
    total = None
    for c in n.child:
        if c.data is not None:
            data = c.data.copy()
            if total is None:
                total = data
            else:
                total += data
    
def prolongate_single(n):
    """Copy data to just the first child."""
    if n.data is not None:
        n.child[0].data = n.data.copy()
    n.data = None
def restrict_single(n):
    """Same as restrict_injection."""
    restrict_injection(n)

def prolongate_datafunc(n):
    """Use the function in the Data class."""
    if n.data is not None:
        for c in n.child:
            c.data = c._data_class(coords=c.coords)
def restrict_datafunc(n):
    """Use the function in the Data class."""
    n.data = n._data_class(coords=n.coords)

            

class Node():
    """
    The main Tree class.
    

    Parameters
    ----------
    name: str
        The name of the node. The name is a string of hexidecimals 
        which trace the node back to the root node of the tree.
        For example, in 3D the 5th child of the root would be called
        0x00x5, and the 7th child of the 3rd child of the root
        would be 0x00x30x7
    dim: int
        The number of dimensions in the tree
    parent: Node
        This node's parent node.
        If None this node is the root of the tree.
    prolongate_func: function
        Function which transfers data to the children of this node when 
        it is split
    restrict_func: function
        Function which transfers from the children of this node when 
        it is unsplit
    xmin: tuple
        The minimum coordinate values for the entire domain
    xmax: tuple
        The maximum coordinate values for the entire domain
    data_class: class
        The Data class used to hold the node's data.
    file: hdf5 group
        The hdf5 group which contains the data

    """
    def __init__(self,name='0x0',dim=2,parent=None,
                prolongate_func=prolongate_single,restrict_func=restrict_single,
                 xmin=None,xmax=None, data_class=Empty,file=None):
        
        # Store some arguments to pass easily to the children
        self.args = {'dim':dim,'xmin':xmin,'xmax':xmax,'prolongate_func':prolongate_func,
                    'restrict_func':restrict_func,'data_class':data_class}
        self.dim = dim
        self.fmt = '0{:d}b'.format(dim)

        self.name = name
        self.global_index = (0,) + tuple([0]*dim)
        self.parent = parent
        self.leaf = True
        self.rflag = False
        self.nchildren = 2**dim
        self.child = [None]*self.nchildren
        self.file = file
        self._data_class = data_class

        self._prolongate_func = prolongate_func
        self._restrict_func = restrict_func
        
        self.xmin = xmin
        self.xmax = xmax
        
        if self.xmin is None:
            self.xmin = [0]*self.dim
        if self.xmax is None:
            self.xmax = [0]*self.dim


    #   Take binary number and return the index relative to parent
        self.index_from_bin = lambda x: tuple(map(int,x))

    #  Take the child index and convert it to binary
    #  Ex: 2 --> '010'
    #      6 --> '110'
        self.tobin = lambda x: format(x,self.fmt)

    #  Take a binary number and convert it to an integer
        self.frombin = lambda x: int(x,base=2)

        self.child_index ={i:self.index_from_bin(self.tobin(i)) for i in range(self.nchildren)}

        self.global_index = self.get_global_index(name)
        self.dx = [(xo-xi)*2.**(-self.global_index[0]) for xi,xo in zip(self.xmin,self.xmax)]
        self.coords = self.get_coords()
        self.data = self._data_class()
        
        
    def save(self,file):
        """
        Write this node to the hdf5 group/file.

        Parameters
        ----------
        file : hdf5 group
            File to write the data to.

        """
        
        gname = '0x' + self.name.split('0x')[-1]
        grp = file.create_group(gname)
        if self.leaf:
            # We are a leaf, so we should dump our data
            dset = grp.create_group('Data')
            self.data.save(dset)
        else:
            # We are not a leaf, so call the children
            for c in self.child:
                c.save(grp)
        return
    def build(self,file):
        """
        Look in the hdf5 group for child cells

        Parameters
        ----------
        file : hdf5 file
            The file we are reading.
        """
        for i in range(self.nchildren):
            try:
                grp = file[hex(i)]
                self.leaf = False
                self.child[i] = Node(self.name+hex(i),parent=self,file=grp,**self.args)
                self.child[i].build(grp)
            except KeyError:
                self.leaf = True
                self.data=Data(coords=self.coords,fname=file['Data'],node=self)
        return
    def get_local_index(self,name):
        """Get the local index relative to the parent from the name."""
        try:
            indx = int(name,base=16)
        except ValueError:
            indx = int( name.split('0x')[-1],base=16)
        binary_name = self.tobin(indx)
        return self.index_from_bin(binary_name)

    def get_global_index(self,name):
        """Calculate the global index from the name."""
        glindx = [0]*self.dim

        names = name.split('0x')[1:]

        level = len(names)-1
        for n in name.split('0x')[1:]:
            lindx = self.get_local_index(n)
            glindx = [2*g+i for g,i in zip(glindx,lindx)]
        return (level,) + tuple(glindx)
    def move_index_up(self,indx):
        """
        Move an index up a level, returning its name and parent index

        Parameters
        ----------
        indx : tuple
            The self.dim dimensional index

        Returns
        -------
        pindx : tuple
            The parent index
        name : str
            The name of the parent 

        """
        pindx = [i//2 for i in indx]
        name = ''.join(map(str,[i%2 for i in indx]))
        name = hex( self.frombin(name) )

        return pindx, name

    def get_level(self,name):
        """Get the level (measured from root) from a name."""
        return len(name.split('0x')[1:])-1

    def get_name(self,indx):
        """Get the name of the cell from the global index."""
        name = []

        level = indx[0]
        if level == 0:
            return hex(0)


        glindx = indx[1:]

        while level > 0:
            glindx, n = self.move_index_up(glindx)
            name.append(n)
            level -= 1
        return hex(0) + ''.join(name[::-1])
    def copy(self):
        """Make a copy of the node."""
        return Node(name=self.name,parent=self.parent,data=self.data,**self.args)
    def deepcopy(self):
        """Make a deep copy of this node"""
        import copy
        return copy.deepcopy(self)
    def restrict(self):
        """Call the node's restrict function."""
        return self._restrict_func(self)
    def prolongate(self):
        """Call the node's prolongate function."""
        return self._prolongate_func(self)
    def split(self):
        """
        Split the node into 2^dim children, and pass the data to the 
        first born.
        Data transfer is handled via the prolongate function.
        """
        self.leaf=False
        self.child[0] = Node(self.name+hex(0),parent=self,**self.args)
        for i in range(1,self.nchildren):
            self.child[i] = Node(self.name+hex(i),parent=self,**self.args)
        self.prolongate()
    def unsplit(self):
        """
        Remove the tree below this node
        Data transfer is handled via the restrict function
        """
        self.restrict()
        self.child = [None]*self.nchildren
        self.leaf = True
    def pop(self):
        """Same as unsplit(), but also returns the tree below"""
        new_tree =  self.deepcopy()
        self.unsplit()
        return new_tree
    def insert(self,name,data=None): 
        """
        Insert a new point in the tree.
        This is the same as find, but will
        grow the tree to accommodate the new point.

        Parameters
        ----------
        name : str
            Name of the point we want to insert
            
        data : class
            Data for the new point

        Returns
        -------
        node : Node
            The node of the new point in the tree.
        """
        
        node = self.find(name,insert=True,data=data)
        return node


    

        
    def up(self):
        """Move up the tree"""
        return self.parent
    def down(self,i=0):
        """Move down the tree to child i."""
        return self.child[i]
    def walk(self,leaf_func=None,node_func=None, target_level=None,
             maxlevel=np.infty):
        """
        Recursively walk the tree.

        Parameters
        ----------
        leaf_func : function
            If not None then call this function if the node 
            is a leaf node.
        node_func :
            If not None then call this function if the node 
            is not a leaf node.
        target_level : int
            Only apply leaf function if this node's leavel is 
            target level.
        maxlevel : int
            Don't go further down in the tree than maxlevel

        """
        if maxlevel is not None:
            if self.global_index[0] > maxlevel:
                return
        if target_level is not None:
            if self.global_index[0] > target_level:
                return
        if self.leaf:
            if target_level is None:
                if leaf_func is not None:
                    leaf_func(self)
            else:
                if self.global_index[0] == target_level:
                    if leaf_func is not None:
                        leaf_func(self)
            return 
        if node_func is not None:
            node_func(self)
        for c in self.child:
            c.walk(leaf_func=leaf_func,node_func=node_func,
                   target_level=target_level,maxlevel=maxlevel)
    def depth(self):
        """Find the depth of the tree."""
        res = [self.global_index[0]]
        func = lambda x: res.append(x.global_index[0])
        self.walk(leaf_func=func)
        return max(res)
    def query(self,point):
        """
        Find the leaf closest to the desired point

        Parameters
        ----------
        point : tuple
            The coordinates of the point we want to find.
            

        Returns
        -------
        leaf : Node
            The leaf node which contains the point.

        """
        
        lvl = self.depth() + 1
        indx = [lvl] +  [int((p-xi)/( (xo-xi)*2.**(-lvl))) for p,xi,xo in zip(point,self.xmin,self.xmax)]
        name = self.get_name(indx)
        leaf = self.find(name)
        return leaf
        
    def find(self,name,insert=False):
        """
        Find the next step towards the node given by name.

        Parameters
        ----------
        name : str
            Name of the node we want to find.
        insert :
           If True then the tree will grow to accomidate the new point
    
        """
        my_level = self.global_index[0]

        names = name.split('0x')[1:]
        target_level = len(names)-1


        if self.name == name:
            # Found it!
            return self
        if my_level < target_level:
            # It's below us so we need to determine which direction to go
            new_name = '0x'+'0x'.join(names[:my_level+1])
            if self.name == new_name:
                # It's one of our descendents
                child = names[my_level+1:][0]
                if self.leaf:
                    # Point doesn't exist currently  
                    if insert:
                        self.split()
                    else:
                        return self
                return self.down(int(child,base=16)).find(name,insert=insert)
        # It's not below us, so move up

        if self.parent is None:
            return None
        return self.up().find(name,insert=insert)
    def find_neighbors(self):
        """
        Find the neighbors and their parents.
        Note that this only finds neighbors with levels <= our level
        """
        import itertools
        level = self.global_index[0]
        indx = self.global_index[1:]

        total_neighbors = 3**self.dim
        offsets = list(itertools.product([-1,0,1],repeat=self.dim))
        

        neighbor_indices = [(level,)+tuple([x+j for j,x in zip(i,indx)]) for i in offsets]

        # Default to None
        neighbors = [None]*total_neighbors
        upper_neighbors = [None]*total_neighbors
        for i,ind in enumerate(neighbor_indices):
            # Check that the point is inside the domain
            if all(j>=0 for j in ind) and all(j<2**ind[0] for j in ind[1:]): 
                n = self.get_name(ind)
                node = self.find(n)
                if node.name == n: 
                    # Node exists at this level
                    neighbors[i] = node
                    upper_neighbors[i] = node.parent
                else: 
                    # Node doesn't exist at this level, we have its parent
                    upper_neighbors[i] = node


        return offsets, neighbor_indices,neighbors, upper_neighbors

        
    def get_coords(self,shift=False):
        """
        Get the data coordinates for this node given xmin and xmax

        Parameters
        ----------
        shift : bool
            If True then return the point in the center of the cell.

        """
        dx = 2.**(-self.global_index[0])
        indx = self.global_index[1:]
        shift = .5 if shift else 0
        return [(i+shift)*dx*(xo-xi) + xi for i,xi,xo in zip(indx,self.xmin,self.xmax)]
    def list_leaves(self,attr='self',func=None,criteria=None):
        """
        Searches the entire tree and returns a list of all of the leaves.

        Parameters
        ----------
        attr : str
            The attribute of the node we want.
            If 'self' the return to whole node object
        func : function
            A function that we apply to the node before
            adding it to the list.
        
        criteria : function
            A filter applied to the final list of leaves.
            Useful for removing None from the list, e.g. 
            criteria = lambda x: x is not None
        Returns
        -------
        leaves : list
            A list of the leaves

        """
        leaves = []
        if func is None:
            if attr is 'self' or attr is 'obj':
                func = lambda i: i
            else:
                func = lambda i: getattr(i,attr)
        
        self.walk(leaf_func=lambda i: leaves.append(func(i)))
        if criteria is not None:
            leaves = list(filter(criteria,leaves))
        return leaves    
    def __repr__(self):
        """Show the name of the node when printed to screen"""
        return self.name
    def __str__(self):
        """Show the name of the node when printed to screen"""
        return self.__repr__(self)

def make_list(leaves,dim=2,Data=None,xmin=None,xmax=None):
    """
    Helper function to construct a tree from a list of leaves.

    Parameters
    ----------
    leaves : list
        A list of names of the leaves we want to add to the tree.
        
    dim : int
        Number of dimensions of the tree
    Data : class
        The data class used by the leaves.
    xmin : tuple
        Minimum coordinate values of the domain
    xmax : tuple
        Maximum coordinate values of the domain

    Returns
    -------
    t : Node
        The final tree

    """
    t = Node(dim=dim,xmin=xmin,xmax=xmax)
    
    for name in leaves:
        t.insert(name)
    
    if Data is not None:
        t.walk(leaf_func=lambda x: setattr(x,'data',Data(coords=x.coords)))
    return t
    
def make_random(nleaves,dim=2,depth=6,Data=None,xmin=None,xmax=None):
    """
    Helper function to construct a tree of random leaves.

    Parameters
    ----------
    nleaves : int    
        Number of leaves to add to the tree
    dim : int
        Number of dimensions of the tree
    depth : int
        The maximum depth of the tree
    Data : class
        The data class used by the leaves.
    xmin : tuple
        Minimum coordinate values of the domain
    xmax : tuple
        Maximum coordinate values of the domain

    Returns
    -------
    t : Node
        The final tree

    """
    t = Node(dim=dim,xmin=xmin,xmax=xmax)
    
    curr_list = []
    num = 0
    while num < nleaves:
        length = np.random.randint(depth)
        name = hex(0) + ''.join([hex(np.random.randint(2**dim)) for i in range(length)])
        if name not in curr_list:
            curr_list.append(name)
            num += 1
            t.insert(name)
    if Data is not None:
        t.walk(leaf_func=lambda x: setattr(x,'data',Data(coords=x.coords)))
    return t
def make_uniform(dim=2,depth=6,Data=None,xmin=None,xmax=None,**kargs):
    """
    Helper function to construct a full tree.

    Parameters
    ----------
    nleaves : int    
        Number of leaves to add to the tree
    dim : int
        Number of dimensions of the tree
    depth : int
        The depth of the tree
    Data : class
        The data class used by the leaves.
    xmin : tuple
        Minimum coordinate values of the domain
    xmax : tuple
        Maximum coordinate values of the domain

    Returns
    -------
    t : Node
        The final tree

    """
    t = Node(dim=dim,xmin=xmin,xmax=xmax,**kargs)
    for i in range(depth):
        for n in t.list_leaves(attr='self'):
            n.split()
    if Data is not None:
        t.walk(leaf_func=lambda x: setattr(x,'data',Data(coords=x.coords)))
    return t
def integrate(tree,dim=-1):
    """
    Integrate over one dimension of the domain.

    Parameters
    ----------
    tree : Node
        The input tree we which to integrate
    dim : int
        The dimension to integrate over
 
    Returns
    -------
    newtree: Node
         A new tree of one less dimension.

    """

    def _func(leaf,dim):
        """Function that returns the index and size of the leaf."""
        lvl = leaf.global_index[0]
        indx = [i for i in leaf.global_index[1:]]
        xmin = [x for x in leaf.xmin]
        xmax = [x for x in leaf.xmax]
        xi = xmin.pop(dim)
        xo = xmax.pop(dim)
        weight = (xo-xi) * 2.**(-lvl)
        k = indx.pop(dim)
        z = xi + weight*k
        if leaf.data is not None:
            data = leaf.data.copy()
        else:
            data = None
        newindx = [lvl] + indx
        return newindx,weight,z,data
        
    maxlevel = tree.depth()
    xmin = [x for x in tree.xmin]
    xi = xmin.pop(dim)
    xmax = [x for x in tree.xmax]
    xo = xmax.pop(dim)
    
    lz = xo-xi
    
                     
    
    newtree = Node(dim=tree.dim-1,xmin=xmin,xmax=xmax)
    vals = []
    for lvl in range(maxlevel+1)[::-1]:
        tree.walk(target_level=lvl,leaf_func=lambda x: vals.append(_func(x,dim)))
    
    for indx,weight,z,data in vals:
        name = newtree.get_name(indx)
        n = newtree.insert(name)
        dx = weight/lz
        if data is not None:
            data = dx*data
            if n.data is None:
                n.data = data.copy()
            else:
                n.data = n.data + data
    return newtree
    
    
    
    
    
