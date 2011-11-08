#!/usr/bin/env python
from urwid_form import TntForm

def test_callback(object_type, object_name, template_name, name, arg_dict):
    import random
    cmf = arg_dict['CMF']
    ip_address = arg_dict['thing']['test_ip2']
    cmf_letters = list(str(cmf))
    random.shuffle(cmf_letters)
    return "(%s) %s: %s" % (name, ''.join(cmf_letters), ip_address)

def main():
    """
    This method gets called only if you run tui_forms.py directly from the command-line.
    It is just for testing.
    """
    form_spec = {
      'object_type': 'router',
      'object_name': 'test_router',
      'template_name': 'big test',
      'variables': {
        'CMF': {
            '^default'    : 999999999,
            '^example'    : 211168045,
            '^label'      : 'CMF ship-to number',
            '^optional'   : True,
            '^type'       : 'integer',
            '^validation' : r'^\d{9}$'
        },
        'sub': {'sub': {
                    'name': {
                        '^type': 'external',
                        '^callback': test_callback,
                        '^weight': 100,
                        '^registered_var_names': ['CMF', 'thing.test_ip2']
                    }}},
        'thing': {
            'test_ip2': {
                '^type' : 'ip_address',
                '^default' : '127.0.0.1',
            },
        },
    #}}
    'deep' : {
        'deeper' : {
            'opt-multi' : {
                '^label' : "What else is awesome?",
                '^type' : 'multi',
                '^optional' : False,
                '^choices' : [
                    'Pirate',
                    'Ninja',
                    'Monkey',
                    'Robot',
                    'Zombie',
                    'Spy',
                    'Dragon',
                ]
            },
        },
        'deepest' : { 'foo' : {}, 'bar' : {} },
    },
    'multi-thing' : {
        '^label' : "Which is the most awesome?",
        '^default' : 'Ninja',
        '^choices' : [
            'Pirate',
            'Ninja',
            'Monkey',
            'Robot',
            'Zombie',
        ]
    },
    'global': {'legal_warning': {
                          '^example': 'Go home, sucker',
                          '^default': '* Access to and use of this device and/or other devices is *\n'\
                                      '* restricted to authorized users only. Unauthorized        *\n'\
                                      '* individuals attempting to access this device may be      *\n'\
                                      '* subject to prosecution.                                  *\n',
                          '^label': 'Legal warning',
                          '^optional': False,
                          '^type': 'long_text',
              },
    },
    'client': {
        'POC': {
            '^example'  : 'DAVID ADLER',
            '^label'    : 'Point-of-contact',
            '^optional' : True,
            '^weight'   : 10,
        },
        'city': {
            '^example'  : 'O FALLON',
            '^label'    : 'Client city',
            '^optional' : False
        },
        'name': {
            '^example'  : 'AUFFENBERG ST CLAIR AUTO MALL',
            '^label'    : 'Client name',
            '^optional' : False,
            '^type'     : 'text'
        },
        'phone_number': {
            '^example'  : '6186242277',
            '^weight'   : 7,
            '^label'    : 'Phone number',
            '^optional' : True,
            '^type'     : 'phone',
        }
    },
    'description': {
        '^default'  : 'This router does not have a description',
        '^example'  : 'DMS over VPN Primary Router',
        '^label'    : 'Router description',
        '^weight'   : 8,
        '^optional' : True,
    },
    'multicheck': {
        '^type' : 'multicheck',
        '^label' : 'PICK THE ROUTERS THAT YOU WANT',
        '^choices' : [
                ('router_1', 'label for router_1'),
                ('router_2', 'label for router_2'),
                ('router_3', 'label for router_3'),
                ('router_4', 'label for router_4'),
                (7, 'label for job_e'),
        ],
        '^optional': True,
    },
    'jobs': {
        '^type' : 'joblist',
        '^label' : 'CHECK THE JOB NAMES THAT THIS COMMENT REFERS TO',
        '^choices' : [
                ('job_a', 'label for job_a'),
                ('job_b', 'label for job_b'),
                ('job_c', 'label for job_c'),
                ('job_d', 'label for job_d'),
                (7, 'label for job_e'),
        ],
    },
    'dc' : {
        '^example' : 'aa',
        '^type' : 'choice',
        '^choices' : ['aa', 'egv'],
        '^optional' : False,
        '^label' : 'Which datacenter?',
    },
}}

    form = TntForm(form_spec)
    values = form()
    pprint(values)

if __name__ == '__main__':
    main()
