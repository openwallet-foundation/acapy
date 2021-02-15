from behave import given, when, then, step

@given(u'an account with "2400" asset points')
def step_impl(context):
    pass

@step(u'the account rofile is tagged as "fraudulent"')
def step_impl(context):
    pass

@when(u'the account owner trades his asset')
def step_impl(context):
    pass

@then(u'the application should prompt an "XXXX" error')
def step_impl(context):
    pass
