from pyramid.config import Configurator

# URL structure:

# /
# /query
# /search

# {docid} = {congress}{type}{number}{status}[-{rev}]
# {congress} = \d+
# {type} = hr
# {number} = \d+
# {status} = ih
# {rev}  = \d+ >= 1

# /bills/{docid} #GET, PUT, POST, DELETE
# /bills/{docid}/view
# /bills/{docid}/edit

# /activity
# /activity/users
# /activity/users/{userid}
# /activity/bills/{docid}

# /users/{userid}

# /vocabularies/{vocab} ?q=""
# /vocabularies/{vocab}/{vocabid}



def main(global_config, **settings):
    """ This function returns a Pyramid WSGI application.
    """
    config = Configurator(settings=settings)
    config.add_route('bill_types', '/')
    config.add_route('dashboard_all', '/dashboard' )
    config.add_route('dashboard', '/dashboard/{billtype}')
    config.add_route('query', '/query')
    config.add_route('bill_create', '/bills/*/create')
    config.add_route('bill_view', '/bills/{docid}/view')
    config.add_route('bill_edit', '/bills/{docid}/edit')
    config.add_route('bill_resource', '/bills/{docid}')
    config.add_route('vocabulary_lookup', '/vocabularies/{vocabid}')
    config.add_route('entity_lookup', '/vocabularies/{vocabid}/{entityid}')
    config.add_route('download', '/download')


    config.add_static_view('Editor', 'static/AKN/Editor')
    config.add_route('akn_editor', 'Editor/Index.html')
    config.add_static_view('static', 'static', cache_max_age=3600)


    config.scan()
    return config.make_wsgi_app()
