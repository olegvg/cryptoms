"""btc reduce bitcoindinstance to hash

Revision ID: 430a023f6d1d
Revises: 3bd4aeb08f66
Create Date: 2018-02-16 18:23:12.686188

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '430a023f6d1d'
down_revision = '3bd4aeb08f66'
branch_labels = None
depends_on = None


def upgrade():
    op.drop_column('bitcoind_instances', 'hostname', schema='btc_public')
    op.drop_column('bitcoind_instances', 'port', schema='btc_public')
    op.drop_column('bitcoind_instances', 'rpc_user', schema='btc_public')
    op.drop_column('bitcoind_instances', 'rpc_passwd', schema='btc_public')
    op.drop_column('bitcoind_instances', 'is_https', schema='btc_public')

    op.add_column('bitcoind_instances', sa.Column('uri_hash', sa.String(64)), schema='btc_public')


def downgrade():
    op.drop_column('bitcoind_instances', 'uri_hash', schema='btc_public')

    op.add_column('bitcoind_instances', sa.Column('hostname', sa.String), schema='btc_public')
    op.add_column('bitcoind_instances', sa.Column('port', sa.Integer), schema='btc_public')
    op.add_column('bitcoind_instances', sa.Column('rpc_user', sa.String), schema='btc_public')
    op.add_column('bitcoind_instances', sa.Column('rpc_passwd', sa.String), schema='btc_public')
    op.add_column('bitcoind_instances', sa.Column('is_https', sa.Boolean), schema='btc_public')
