NAME = 'name'
STATE = 'state'
DRIFTS = 'drifts'
IS_DRIFTED = 'is_drifted'
MASKED_ENV_VARS = {
    'AWS_ACCESS_KEY_ID',
    'AWS_SECRET_ACCESS_KEY'
}
TERRAFORM_BACKEND = \
    """
  backend "%s" {
%s
  }
"""
TERRAFORM_STATE_FILE = 'terraform.tfstate'
