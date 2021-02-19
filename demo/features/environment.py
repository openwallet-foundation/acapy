from runners.agent_container import AgentContainer
from bdd_support.agent_backchannel_client import (
    aries_container_terminate,
)


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
    print(">>> after_scenario activated")

    # shut down any agents that were started for the scenario
    if "active_agents" in context:
        print(">>> shutting down active agents ...")
        for agent_name in context.active_agents.keys():
            print("    shutting down:", agent_name)
            agent = context.active_agents[agent_name]["agent"]
            if agent:
                terminated = aries_container_terminate(agent)
                print("    terminated:", terminated)


def before_step(context, step):
    pass


def after_step(context, step):
    pass


def before_all(context):
    pass


def after_all(context):
    pass
