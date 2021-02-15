
def before_feature(context, feature):
    pass

def after_feature(context, feature):
    pass

def before_tag(context, tag):
    pass

def after_tag(context, tag):
    pass
    
def before_scenario(context, scenario):
    print(">>> before_scenario activated")

def after_scenario(context, step):
    # shut down any agents that were started for the scenario
    print(">>> after_scenario activated")

def before_step(context, step):
    pass

def after_step(context, step):
    pass

def before_all(context):
    pass
    
def after_all(context):
    pass

