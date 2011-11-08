urwid_form
==========

This is a fairly simply module that will allow you to craft up a form for basic user input rapidly and with a minimum of fuss.

in scripts/form_test.py, there is a basic example of how to drive the system. You're going to import Form from urwid_form, and then you'' pass it a dictionary that you would like filled out.

The dictionary to pass Form must have at least the 'variables' section defined. Underneath that section can be an arbitrarily deep set of dictionaries until you want to define a field that you would like filled in by th user.

Fields to be filled in by the user are identified by having one or more keys that start with '^'

The following field directives are accepted by the system:

 * ^type  - this can be either 'int', 'text', 'longtext', 'choice', or 'multi'
 * ^choices  - If the *type* above is either 'choice' or 'multi', then this field represents the list of choices available to the user
 * ^optional  - whether or not the field can be ignored by the user (default: False)
 * ^default  - what the pre-filled-in variable is (or pre-selected in the case of a checkbox)

An example of an input dictionary would be the following:

<pre>
input_dict = {'variables': {
                  'section_1': {  
                      'text_var': {'^type': 'text',
                                   '^default': 'a brown cat',
                                   '^optional: 'true'},
                      'choice_var': {'^type': 'choice',
                                     '^choices': ['a', 'b', 'c'],
                                     '^default': 'b'},
             }}}
</pre>

Calling the form is as simple as:

<pre>
import urwid_form
form = urwid_form.Form(input_dict)
values = form()
print values
</pre>

A curses-based form pops up when the form in called. Any fields that are mandatory that are not filled in will be highlighted if the user attempts to save without providing those values. Once all the values are provided, the new dictionary created (in this case, 'values'), will have the same structure as the original dictionary, except all the values will be filled in with real data instead of definition information. For example:

<pre>
values = {'variables': {
                  'section_1': {  
                      'text_var': 'a yellow cat',
                      'choice_var': 'a',
             }}}
</pre>
