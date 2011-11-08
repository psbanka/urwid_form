#!/usr/bin/env python
"""simple module to create a curses-based form"""

import urwid
import re

def get_var(input_dict, accessor_string):
    """Gets data from a dictionary using a dotted accessor-string"""
    current_data = input_dict
    for chunk in accessor_string.split('.'):
        current_data = current_data.get(chunk, {})
    return current_data

STATUS_LINE  = 'status_line'
EDIT_LABEL   = 'edit_label'
TEXT_UNFOCUS = 'text_unfocus'
EDIT_FOCUS   = 'edit_focus'
EDIT_UNFOCUS = 'edit_unfocus'
ERR_FOCUS    = 'err_focus'
ERR_UNFOCUS  = 'err_unfocus'

NONE = "<NONE>"
READ_WRITE = 'read_write'
READ_ONLY = 'read_only'

# Exceptions to handle DialogDisplay exit codes

def _get_original(widget):
    if hasattr(widget, 'original_widget'):
        return _get_original(widget.original_widget)
    return widget

class DialogExit(Exception):
    def __init__(self, exitcode = 0):
        self.exitcode = exitcode

class ChildDialogExit(DialogExit):
    pass

class MainDialogExit(DialogExit):
    pass

# MyFrame makes urwid.Frame switch
# focus between body and footer
# when pressing 'tab'

class MyFrame(urwid.Frame):
    def keypress(self, size, key):
        if key == 'tab':
            if self.focus_part == 'body':
                self.set_focus('footer')
                return None
            elif self.focus_part == 'footer':
                self.set_focus('body')
                return None
            else:
                # do default action if
                # focus_part is 'header'
                self.__super.keypress(size, key)
        return self.__super.keypress(size, key)


class DialogDisplay(urwid.WidgetWrap):
    """
    Shows a popup dialog box
    """
    parent = None
    def __init__(self, text, width, height, body=None, loop=None):
        width = int(width)
        if width <= 0:
            width = ('relative', 80)
        height = int(height)
        if height <= 0:
            height = ('relative', 80)

        if body is None:
            # fill space with nothing
            self.body = urwid.SolidFill(' ')
            fp = 'footer'
        else:
            self.body = body
            fp = 'body'
        self.frame = MyFrame(self.body, focus_part = fp)
        if text is not None:
            self.frame.header = urwid.Pile( [urwid.Text(text),
                urwid.Divider(u'\u2550')] )
        w = self.frame

        # pad area around listbox
        w = urwid.Padding(w, ('fixed left',2), ('fixed right',2))
        w = urwid.Filler(w, ('fixed top',1), ('fixed bottom',1))
        w = urwid.AttrWrap(w, 'body')

        w = urwid.LineBox(w)

        # "shadow" effect
        w = urwid.Columns( [w,('fixed', 1, urwid.AttrWrap(
            urwid.Filler(urwid.Text(('border',' ')), "top")
            ,'shadow'))])
        w = urwid.Frame( w, footer =
            urwid.AttrWrap(urwid.Text(('border',' ')),'shadow'))
        if loop is None:
            # this dialog is the main window
            # create outermost border area
            w = urwid.Padding(w, 'center', width )
            w = urwid.Filler(w, 'middle', height )
            w = urwid.AttrWrap( w, 'border' )
        else:
            # this dialog is a child window
            # overlay it over the parent window
            self.loop = loop
            self.parent = self.loop.widget
            w = urwid.Overlay(w, self.parent, 'center', width+2, 'middle', height+2)
        self.view = w

        # Call WidgetWrap.__init__ to correctly initialize ourselves
        urwid.WidgetWrap.__init__(self, self.view)
        self.is_alive = None

    def add_buttons(self, buttons):
        l = []
        for name, exitcode in buttons:
            b = urwid.Button( name, self.button_press )
            b.exitcode = exitcode
            b = urwid.AttrWrap( b, 'button normal','button select' )
            l.append( b )
        self.buttons = urwid.GridFlow(l, 10, 3, 1, 'center')
        self.frame.footer = urwid.Pile( [ urwid.Divider(u'\u2500'),
            self.buttons ], focus_item = 1)

    def button_press(self, button):
        if self.parent is None:
            # We are the main window,
            # so raise an exception to
            # quit the main loop
            raise MainDialogExit(button.exitcode)
        else:
            # We are a child window,
            # so restore the parent widget
            # then raise a ChildDialogExit exception
            self.loop.widget=self.parent
            raise ChildDialogExit(button.exitcode)

    def exit(self):
        self.loop.widget=self.parent

    def show(self):
        if self.loop is None:
            self.loop = urwid.MainLoop(self.view, self.palette)
            exited = False
            while not exited:
                try:
                    self.loop.run()
                except ChildDialogExit as e:
                    # Determine which dialog has exited
                    # and act accordingly
                    pass
                except MainDialogExit:
                    exited = True
        else:
            self.loop.widget = self.view

class Form(object):
    """
    Main form class.  Returned object is callable
    """
    def __init__(self, form_spec):
        """
        We're setting up a SimpleListWalker which will contain
        all of the items we're trying to edit on the screen.
        @param form_spec: A dictionary of the form: {'variables': {}}
        which will call out all of the items that we want to edit.
        """
        self.walker = urwid.SimpleListWalker([])

        # self.base_form_element is a list of (a list of) widgets
        self.base_form_element = NestedFormElement(form_spec['variables'], '', None)
        self.template_name = form_spec['template_name']
        self.object_type = form_spec['object_type']
        self.object_name = form_spec['object_name']

        for widget in self.base_form_element.make_widgets():
            self.walker.append(widget)

        self.body = urwid.ListBox(self.walker)
        frame = urwid.Frame(
            body   = self.body,
            header = self._banner(),
            footer = self._banner(),
        )
        self.loop = urwid.MainLoop(
            frame,
            self._my_palette(),
            unhandled_input = self._keypress,
        )
        self.aborted = False
        self.complete = False
        self.popup = None

    def _get_registered_vars(self, var_names):
        "Pull registered variable data out of our form"

        values = {}
        values.update(self.base_form_element.get_value())
        return values['']

    def update_labels(self):
        # This approach seems pretty gross, but it's the only way I could see
        # to actually get urwid to update the labels -pbanka

        start_widget, position = self.body.get_focus()

        # iterate through all the widgets until we get back to where we started
        while True:
            self.body.set_focus((position + 1) % len(self.walker))
            focus_widget, position = self.body.get_focus()
            if focus_widget == start_widget:
                break
            original = _get_original(focus_widget)
            if hasattr(original, 'callback'):
                var_names = original.registered_var_names
                var_dict = self._get_registered_vars(var_names)
                original.callback(self.object_type, self.object_name,
                                  self.template_name, var_dict)

    def _my_palette(self):
        """defines the styles to be applied to various parts of the form"""
        return (
            (STATUS_LINE    , 'white'      , 'dark red'   ),
            (EDIT_LABEL     , 'default'    , 'black'      ),
            (EDIT_FOCUS     , 'white'      , 'light blue' ,  'bold' ),
            (EDIT_UNFOCUS   , 'light gray' , 'dark blue'  ),
            (TEXT_UNFOCUS   , 'light gray' , 'black'  ),
            (ERR_FOCUS      , 'white'      , 'light red'  ,  'bold' ),
            (ERR_UNFOCUS    , 'light gray' , 'dark red'   ),
            # Dialog box colors
            ('border'       , 'black'      , 'black'),
            ('shadow'       , 'white'      , 'black'),
            ('button normal', 'light gray' , 'dark blue'  , 'standout'),
        )

    def _banner(self):
        """Text to be used for the top and bottom lines of the screen"""
        txt =  urwid.Text('Press F10 to save & exit; F4 to cancel', align = 'center')
        return urwid.AttrMap(txt, STATUS_LINE)

    def __call__(self):
        """Run the form & return its values"""
        while not self.aborted and not self.complete:
            try:
                self.loop.run()
            except ChildDialogExit as cde:
                pass
        if self.aborted:
            raise KeyboardInterrupt
        values = {}
        values.update(self.base_form_element.get_value())
        return values['']

    def _popup(self, msg):
        "Dialog box to show a message"
        widgets = [urwid.Text(msg)]
        listbox = urwid.ListBox(urwid.SimpleListWalker([urwid.AttrWrap(w, None, 'reveal focus') for w in widgets]))
        self.popup = DialogDisplay( "Error in input", 50, 10, listbox, self.loop)
        self.popup.add_buttons([    ("OK", 0) ])
        self.popup.show()

    def _keypress(self, keycode):
        """handler for keystrokes not handled by default"""
        if self.popup:
            self.popup.exit()
            self.popup = None
        if keycode not in ('tab', 'shift tab', 'enter', 'f10', 'f4'):
            return

        if keycode == 'f10':
            if self.base_form_element.validate():
                self.complete = True
                raise urwid.ExitMainLoop()
            else:
                # pop a message
                text = "Some fields missing or invalid. "\
                       "Fields that need attention are highlighted in red."
                self._popup(text)
        elif keycode == 'f4':
            self.aborted = True
            raise urwid.ExitMainLoop()
        else:
            self.update_labels()
            if keycode == 'shift tab':
                offset = -1
            else: # keycode == 'tab'
                offset = 1
            while True:
                focus_widget, position = self.body.get_focus()
                self.body.set_focus((position + offset) % len(self.walker))
                focus_widget, position = self.body.get_focus()
                if focus_widget.selectable():
                    break

def build_me_a_form(form_spec, parent = None):
    """
    helper function to build a list of widgets for a form & figure out nesting
    This is called recursively to create FormElements and NestedFormElements.
    """
    if parent == None:
        parent = NestedFormElement(form_spec, '', None)

    form_elements = []
    for name, spec_dict in form_spec.items():
        new_form_element = None
        if type(spec_dict) != dict:
            raise Exception('Malformed form dictionary')
        if all(key.startswith('^') for key in spec_dict):
            # If all elements have a '^', we have a proper FormElement
            # define
            new_form_element = FormElement(spec_dict, name, parent)
        elif any(key.startswith('^') for key in spec_dict):
            raise Exception('Improperly formed form dictionary')
        else:
            new_form_element = NestedFormElement(spec_dict, name, parent)
        form_elements.append(new_form_element)

    return sorted(form_elements, key=lambda x: x.weight, reverse=True)

class AbstractFormElement(object):

    def __init__(self, name, parent):
        self.name = name
        self.parent = parent

    def tree_lines(self, child):
        yield str(child)
        if hasattr(child, 'get_children'):
            children = child.get_children()
            last = children[-1] if children else None
            for child in children:
                connect_chr = '-'
                prefix = '`-' if child is last else '+-'
                for line in self.tree_lines(child):
                    yield prefix + line
                    prefix = '  ' if child is last else '| '

    def get_full_name(self):
        if self.parent == None:
            return self.name
        else:
            return "%s.%s" % (self.parent.get_full_name(), self.name)

    def get_base_parent(self):
        "Want to obtain the top-most parent in the structure"
        if self.parent == None:
            return self
        return self.parent.get_base_parent()

    def get_children(self):
        raise AbstractMethod()

    def make_widgets(self):
        raise AbstractMethod()

    def get_value(self):
        raise AbstractMethod()

    def validate(self):
        raise AbstractMethod()

    def __repr__(self):
        raise AbstractMethod()

class FormElement(AbstractFormElement):
    """This class handles every sort of form element that we can dream up"""

    def __init__(self, spec_dict, name, parent):
        """
        Pull out specification information that is relevant to the form
        itself. There may be items in the spec that we don't care about
        """
        AbstractFormElement.__init__(self, name, parent)
        self.label = spec_dict.get('^label', name)
        self.default = spec_dict.get('^default', '')
        self.type = spec_dict.get('^type', 'text')
        self.validate_str = spec_dict.get('^validation', None)
        self.optional = spec_dict.get('^optional', False)
        self.choices = spec_dict.get('^choices')
        self.weight = spec_dict.get('^weight', 0)
        self.callback = spec_dict.get('^callback', lambda : '--')
        self.registered_var_names = spec_dict.get('^registered_var_names', [])
        self.widgets = None

    def get_children(self):
        if self.widgets is None:
            return []
        return self.widgets

    def make_widgets(self):
        """
        Creates a set of widgets, sets self.widgets, and returns them.
        Each widget that is created is based on self.type
        """
        if self.optional:
            required_marker = ''
        else:
            required_marker = '*'

        style = READ_WRITE
        caption = (EDIT_LABEL, "%s%s: " % (required_marker, self.label))
        if type(caption) == int:
            caption = str(caption)
        if type(self.default) == int:
            self.default = str(self.default)

        if self.type == 'integer':
            widgets = [BetterInt(caption, self.default, self.validate_str)]
        elif self.type == 'ip_address':
            widgets = [IpEdit(caption, self.default, self.validate_str)]
        elif self.type == 'long_text':
            widgets = [urwid.Edit(caption, self.default, multiline=True)]
        elif self.type == 'multi' and self.choices:
            widgets = CheckBoxSetFactory(caption, self.choices, self.optional)
        elif self.type == 'multicheck':
            widgets = MultiCheckFactory(caption, self.choices, self.optional)
        elif self.type == 'joblist':
            widgets = JobCommentFactory(caption, self.choices)
        elif self.type == 'external':
            widgets = [TextDisplay(self, self.name, self.label, self.callback, self.registered_var_names)]
            self.optional = True
            style = READ_ONLY
        elif self.choices:
            widgets = RadioSetFactory(caption, self.default, self.choices, self.optional)
        else:
            widgets = [EditValidator(caption, self.default, self.validate_str)]

        self.widgets = []
        for widget in widgets:
            if style == READ_WRITE:
                self.widgets.append(urwid.AttrMap(widget, EDIT_UNFOCUS, EDIT_FOCUS))
            else:
                self.widgets.append(urwid.AttrMap(widget, TEXT_UNFOCUS, TEXT_UNFOCUS))
        return self.widgets

    def get_value(self):
        """get the value of the wrapped widget"""
        child_values = []
        for widget in self.widgets:
            if hasattr(widget.original_widget, 'get_edit_text'):
                child_value = widget.original_widget.get_edit_text()
                child_values.append(child_value)
        if len(child_values) == 0:
            child_values = None
        elif len(child_values) == 1 and self.type != 'multi':
            child_values = child_values[0]

        return {self.name: child_values}

    def validate(self):
        """figure out if the wrapped widget has a valid value"""
        valid = True

        for widget in self.widgets:
            if hasattr(widget.original_widget, 'validate'):
                if not widget.original_widget.validate():
                    valid = False

        if not self.optional:
            value_dict = self.get_value()
            for key, value in value_dict.iteritems():
                if not value:
                    valid = False

        if not valid:
            unfocus, focus = ERR_UNFOCUS, ERR_FOCUS
        else:
            unfocus, focus = EDIT_UNFOCUS, EDIT_FOCUS

        for widget in self.widgets:
            widget.set_attr_map({None:unfocus})
            widget.set_focus_map({None:focus})

        return valid

    def __repr__(self):
        return "Form of: %s" % (self.widgets)

    def __str__(self):
        return self.name

class NestedFormElement(AbstractFormElement):
    """
    Dictionaries that we're passing into tui_forms are nested.
    We want to reflect that nesting in the form itself.
    """
    def __init__(self, spec_dict, name, parent):
        AbstractFormElement.__init__(self, name, parent)
        self.form_elements = build_me_a_form(spec_dict, self)
        self.weight = max([x.weight for x in self.form_elements])

    def get_children(self):
        return self.form_elements

    def make_widgets(self):
        """return a list of widgets with a label prepended"""
        label = urwid.Text((EDIT_LABEL, self.name))
        label._selectable = False
        widgets = [label] # FIXME: should not be selectable
        for form_element in self.form_elements:
            for widget in form_element.make_widgets():
                widgets.append(urwid.Padding(widget, left=4))
        return widgets

    def get_value(self):
        """return the value of all form_element elements"""
        form_element_values = {}
        for form_element in self.form_elements:
            form_element_values.update(form_element.get_value())
        return {self.name : form_element_values}

    def validate(self):
        """
        perform validation of all form_element elements & aggregate results
        """
        # must evaluate all of them to ensure updating
        valid = True
        for form_element in self.form_elements:
            if not form_element.validate():
                valid = False
        return valid

    def __repr__(self):
        return "Nested Form of: %s" % (self.form_elements)

    def __str__(self):
        return "NESTED FORM: %s" % self.name

class EditValidator(urwid.Edit, object):
    """
    Provide a hook for basic input validation using the ^validation directive
    """
    def __init__(self, caption, default, validate_str):
        """
        New up an edit Validator
        """
        #noinspection PyArgumentList
        if isinstance(default, float):
            default = str(int(default))
        urwid.Edit.__init__(self, caption, default)
        self.validator = None
        if validate_str:
            self.validator = re.compile(validate_str)

    def validate(self):
        txt = self.get_edit_text()
        if txt is None:
            txt = ''
        elif type(txt) not in [str, unicode]:
            txt = str(txt)
        if self.validator:
            try:
                if not self.validator.findall(txt):
                    return False
            except:
                raise Exception(type(txt))
        return True

    def __repr__(self):
        return "EditValidator (%s)" % self.caption

class BetterInt(EditValidator):
    """
    Wrap IntEdit to give it a get_edit_text() so its consistent with the
    rest of our widgets
    """
    def __init__(self, caption, default, validate_str):
        EditValidator.__init__(self, caption, default, validate_str)

    def valid_char(self, char):
        return char in "1234567890"

    def get_edit_text(self):
        """
        Over ride our super class' get_edit_text in order to return an int.
        """
        txt = super(BetterInt, self).get_edit_text()
        try:
            return int(txt)
        except ValueError:
            return None
        except TypeError:
            return None

    def __repr__(self):
        return "BetterInt (%s)" % self.caption

class IpEdit(EditValidator):
    """Text edit subclass that only allows IP adresses"""
    def __init__(self, caption, default, validate_str):
        EditValidator.__init__(self, caption, default, validate_str)

    def valid_char(self, char):
        return char in "1234567890."

    def validate(self):
        if not EditValidator.validate(self):
            return False
        txt = self.get_edit_text()
        quads = txt.split('.')
        if len(quads) != 4:
            return False
        return all(x and 0 <= int(x) <= 255 for x in quads)

    def __repr__(self):
        return "IpEdit (%s)" % self.caption

class TextDisplay(urwid.Text):
    """
    This is a widget that displays text to the user and is read-only
    """
    def __init__(self, parent, name, caption, update_function, registered_var_names):
        self.parent = parent
        self.name = name
        self.caption = caption
        self.update_function = update_function
        self.registered_var_names = registered_var_names
        urwid.Text.__init__(self, "%s: ---" % self.caption)

    def validate(self):
        return True

    def callback(self, object_type, object_name, template_name, var_dict):
        full_name = self.parent.get_full_name()[1:]
        output = self.update_function(object_type, object_name, template_name,
                                      full_name, var_dict)
        text = "%s: %s" % (self.caption, output)
        self.set_text(text)

    def __str__(self):
        return "TextWidget: %s" % self.caption

class RadioSet(urwid.WidgetWrap):
    """Class to represent a set of radio buttons from a list of options"""
    def __init__(self, default=None, choices=None, optional=False):
        if choices is None:
            choices = []

        self.choices = choices
        self.optional = optional
        self.default = default
        self.radios = []

        if self.optional:
            # Make the 'none of the above' widget
            urwid.RadioButton(self.radios, NONE)

        state = lambda s: (self.default and s == default) or "first True"

        for c in choices:
            urwid.RadioButton(self.radios, c, state(c))

        max_length = max(len(c) for c in choices)
        if max_length < 16:
            cell_width = max_length+4
        else:
            cell_width = 20

        radio_grid = urwid.GridFlow(self.radios, cell_width, 1, 1, 'left')
        urwid.WidgetWrap.__init__(self, radio_grid)

    def get_edit_text(self):
        for r in self.radios:
            if r.get_state():
                if self.optional and r.get_label() == NONE:
                    return None
                else:
                    return r.get_label()

    def validate(self):
        return True

    def __repr__(self):
        return "RadioSet (%s)" % self.choices

def RadioSetFactory(caption, default=None, choices=[], optional=False):
    """factory method for a RadioSet with a label"""
    cap = urwid.Text(caption)
    radios = RadioSet(default, choices, optional)
    return [cap, radios]

class CheckBoxSet(urwid.WidgetWrap):
    """A set of linked checkbox widgets"""
    def __init__(self, choices=[], optional=False, default_state=False):
        self.optional = optional
        choices = [ str(c) for c in choices ]
        self.choices = choices
        self.boxes = [urwid.CheckBox(c, state=default_state) for c in choices]

        max_length = max(len(c) for c in choices)
        if max_length < 16:
            cell_width = max_length+4
        else:
            cell_width = 20

        box_grid = urwid.GridFlow(self.boxes, cell_width, 1, 1, 'left')
        urwid.WidgetWrap.__init__(self, box_grid)

    def get_edit_text(self):
        return [b.get_label() for b in self.boxes if b.get_state()]

    def validate(self):
        if not self.optional:
            return len(self.get_edit_text()) > 0

        return True

    def __repr__(self):
        return "CheckBoxSet (%s)" % self.choices

def CheckBoxSetFactory(caption, choices=[], optional=False, default_state=False):
    """factory method for CheckBoxSet with a label"""
    cap = urwid.Text(caption)
    boxes = CheckBoxSet(choices, optional, default_state)
    return [cap, boxes]

def MultiCheckFactory(caption, choices, optional):
    """
        Input widget for more than one thing that can be picked,
        has checkboxes and descriptions of each thing
    """
    if optional:
        caption = (caption[0], "(OPTIONAL) " + caption[1])
    cap = urwid.Text(caption)
    div = urwid.Divider('-', 0, 0)

    checks = CheckBoxSetFactory('', [c[0] for c in choices], default_state=False, optional=optional)
    description = [div] + [urwid.Text("%s : %s" % (c[0], c[1])) for c in choices] + [div]

    #return [cap, div] + checks + description
    return [cap] + checks + description

def JobCommentFactory(caption, choices):
    """
        Input widget for job comments, has a text field, checkboxes for applicable jobs
        & descriptions of the jobs
    """
    cap = urwid.Text(caption)
    txt = urwid.Edit('','', True)
    div = urwid.Divider('-', 0, 1)

    checks = CheckBoxSetFactory('', [c[0] for c in choices], default_state=True)
    jobs = [urwid.Text("%s : %s" % (c[0], c[1])) for c in choices]

    return [cap, txt, div] + checks + jobs

