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



def main(global_config, **settings):
    """ This function returns a Pyramid WSGI application.
    """
    config = Configurator(settings=settings)
    config.add_static_view('static', 'static', cache_max_age=3600)
    config.add_route('dashboard', '/')
    config.add_route('query', '/query')
    config.add_route('bill_view', '/bills/{docid}/view')
    config.add_route('bill_edit', '/bills/{docid}/edit')
    config.add_route('bill_resource', '/bills/{docid}')
    
    config.scan()
    return config.make_wsgi_app()
