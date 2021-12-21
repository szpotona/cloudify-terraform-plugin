NAME = 'name'
STATE = 'state'
DRIFTS = 'drifts'
IS_DRIFTED = 'is_drifted'
MASKED_ENV_VARS = {
    'AWS_ACCESS_KEY_ID',
    'AWS_SECRET_ACCESS_KEY'
}
TERRAFORM_BACKEND = """{indent}backend "{name}" {{
{value}
{indent}}}
"""
TERRAFORM_STATE_FILE = 'terraform.tfstate'
HCL_DICT_TEMPLATE = """{indent}{name} {{
{indent}{value}
{indent}{indent}}}
"""
HCL_STR_TEMPLATE = '{indent}{name} = "{value}"\n'
