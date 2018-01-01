def includeme(config):

    #config.add_static_view('static', 'static', cache_max_age=3600)

    config.add_route('/', '/')
    
    # scraper_runs
    config.add_route('/api/v1/scraper_runs', '/api/v1/scraper_runs')

    # dispatches
    config.add_route('/api/v1/dispatches', '/dispatches')
    config.add_route('/api/v1/dispatches/_publish', '/api/v1/dispatches/_publish')
    config.add_route('/api/v1/dispatches/_cleanup', '/api/v1/dispatches/_cleanup')
    config.add_route('/api/v1/dispatches/{id}', '/api/v1/dispatches/{id}')

    # call_types
    config.add_route('/api/v1/call_types', '/api/v1/call_types')
    config.add_route('/api/v1/call_types/{id}', '/api/v1/call_types/{id}')

    # addresses
    config.add_route('/api/v1/addresses', '/api/v1/addresses')
    config.add_route('/api/v1/addresses/_query', '/api/v1/addresses/_query')
    config.add_route('/api/v1/addresses/{id}', '/api/v1/addresses/{id}')

    # agencies
    config.add_route('/api/v1/agencies', '/api/v1/agencies')
    config.add_route('/api/v1/agencies/{id}', '/api/v1/agencies/{id}')

    # incidents
    config.add_route('/api/v1/incidents', '/api/v1/incidents')
    config.add_route('/api/v1/incidents/{id}', '/api/v1/incidents/{id}')    

    # settings
    config.add_route('/api/v1/settings', '/api/v1/settings')
    config.add_route('/api/v1/settings/{id}', '/api/v1/settings/{id}')
