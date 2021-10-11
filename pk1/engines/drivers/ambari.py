from ambari.client import Client

def list_engines(host):
    c=Client('http://{}:8080'.format(host))
    engines=[]
    for s in c.stack_services():
        engines.append({
            'name':s['StackServices']['service_name'],
            'description':s['StackServices']['comments']
        })
    return engines

def list_components(host,engine):
    c=Client('http://{}:8080'.format(host))
    components=[]
    for cpn in c.stack_service_components(service_name=engine):
        components.append({
            'name':cpn['StackServiceComponents']['component_name'],
            'type':cpn['StackServiceComponents']['component_category'].lower()
        })
    return components