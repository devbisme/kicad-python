from kigadgets import pcbnew_bare as pcbnew

from kigadgets import Point, Size, DEFAULT_UNIT_IUS, SWIGtype, SWIG_version, instanceof
from kigadgets.item import HasPosition, HasOrientation, Selectable, HasLayer, BoardItem, TextEsque
from kigadgets.pad import Pad
from kigadgets.layer import get_board_layer_name


class FootprintLabel(HasPosition, HasLayer, Selectable, BoardItem, TextEsque):
    """wrapper for `TEXTE_MODULE` or (old) `FP_TEXT`"""
    _wraps_native_cls = SWIGtype.FpText

    def __init__(self, mod, text=None, layer=None):
        self._obj = SWIGtype.FpText(mod.native_obj)
        mod.native_obj.Add(self._obj)
        if text:
            self.text = text
        if layer:
            self.layer = layer

    @property
    def visible(self):
        try:
            return self._obj.IsVisible()
        except AttributeError:
            raise AttributeError('FootprintLabel.visible is write only in KiCad v{}'.format(SWIG_version))

    @visible.setter
    def visible(self, value):
        return self._obj.SetVisible(value)


class FootprintLine(HasLayer, Selectable, BoardItem):
    """Wrapper for `EDGE_MODULE` or (old) `FP_SHAPE`"""
    _wraps_native_cls = SWIGtype.FpShape


class Footprint(HasPosition, HasOrientation, Selectable, BoardItem):
    _ref_label = None
    _val_label = None
    _wraps_native_cls = SWIGtype.Footprint

    def __init__(self, ref=None, pos=None, board=None):
        if not board:
            from kigadgets.board import Board
            try:
                board = Board.from_editor()
            except:
                board = None
        self._obj = SWIGtype.Footprint(board.native_obj)
        if ref:
            self.reference = ref
        if pos:
            self.position = pos
        if board:
            board.add(self)

    @property
    def reference(self):
        return self._obj.GetReference()

    @reference.setter
    def reference(self, value):
        self._obj.SetReference(value)

    @property
    def reference_label(self):
        native = self._obj.Reference()
        if self._ref_label is None or self._ref_label.native_obj is not native:
            self._ref_label = FootprintLabel.wrap(native)
        return self._ref_label

    @property
    def value(self):
        return self._obj.GetValue()

    @value.setter
    def value(self, value):
        self._obj.SetValue(value)

    @property
    def value_label(self):
        native = self._obj.Value()
        if self._val_label is None or self._val_label.native_obj is not native:
            self._val_label = FootprintLabel.wrap(native)
        return self._val_label

    @property
    def graphical_items(self):
        """Text and drawings of module iterator."""
        def wrap_both(item):
            if instanceof(item, SWIGtype.FpShape):
                return FootprintLine.wrap(item)
            elif instanceof(item, SWIGtype.FpText):
                return FootprintLabel.wrap(item)
            else:
                raise Exception("Unknown module item type: {}".format(type(item)))
        return [wrap_both(item) for item in self._obj.GraphicalItems()]

    def flip(self):
        if SWIG_version >= 7:
            self._obj.Flip(self._obj.GetCenter(), True)
        else:
            self._obj.Flip(self._obj.GetCenter())

    @property
    def layer(self):
        return get_board_layer_name(self.board, self._obj.GetLayer())

    @layer.setter
    def layer(self, value):
        if value == self.layer:
            return
        if value not in ['F.Cu', 'B.Cu']:
            raise ValueError("You can place a module only on 'F.Cu' or 'B.Cu' layers!")
        # Using flip will make sure all components of the module are
        # switched to correct layer
        self.flip()

    @property
    def lib_name(self):
        return self._obj.GetFPID().GetLibNickname().GetChars()

    @property
    def fp_name(self):
        return self._obj.GetFPID().GetLibItemName().GetChars()

    def copy(self, ref, pos=None, board=None):
        """Create a copy of an existing module on the board
            A new reference designator is required, example:

                mod2 = mod1.copy('U2')
                mod2.reference == 'U2'  # True
        """
        if SWIG_version >= 7:
            _module = SWIGtype.Footprint(self._obj)
        else:
            _module = SWIGtype.Footprint(board and board._obj)
            _module.Copy(self._obj)
        module = Footprint.wrap(_module)
        module.reference = ref
        if pos:
            module.position = pos
        if board:
            board.add(module)
        elif self.board:
            self.board.add(module)
        return module

    @property
    def pads(self):
        return [Pad.wrap(p) for p in self._obj.Pads()]

    def remove(self, element, permanent=False):
        ''' Makes it so Ctrl-Z works.
            Keeps a reference to the element in the python pcb object,
            so it persists for the life of that object
        '''
        if not permanent:
            if not hasattr(self, '_removed_elements'):
                self._removed_elements = []
            self._removed_elements.append(element)
        self._obj.Remove(element._obj)

    def restore_removed(self):
        if hasattr(self, '_removed_elements'):
            for element in self._removed_elements:
                self._obj.Add(element._obj)
        self._removed_elements = []

    def geohash(self):
        mine = hash((
            self.reference,
            self.value,
            self.layer,
            # self.lib_name,
            self.fp_name
        ))

        child_hashes = []
        for p in self.pads:
            child_hashes.append(p.geohash())
        for d in self.graphical_items:
            child_hashes.append(d.geohash())
        child_hashes.sort()
        mine += hash(tuple(child_hashes))
        return mine + super().geohash()


# In case v5 naming is used
Module = Footprint
ModuleLine = FootprintLine
ModuleLabel = FootprintLabel
