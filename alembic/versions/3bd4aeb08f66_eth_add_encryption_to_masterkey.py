"""eth_add_encryption_to_masterkey

Revision ID: 3bd4aeb08f66
Revises: e2f73f2ac60a
Create Date: 2018-02-15 18:16:19.137565

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '3bd4aeb08f66'
down_revision = 'e2f73f2ac60a'
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column('master_keys', 'seed', schema='eth_private', new_column_name='seed_encrypted',
                    type_=sa.String(256))
    op.add_column('master_keys', sa.Column('seed_aet', sa.String(32), unique=True), schema='eth_private')
    op.add_column('master_keys', sa.Column('seed_nonce', sa.String(32), unique=True), schema='eth_private')


def downgrade():
    op.alter_column('master_keys', 'seed_encrypted', schema='eth_private', new_column_name='seed',
                    type_=sa.String)
    op.drop_column('master_keys', 'seed_aet', schema='eth_private')
    op.drop_column('master_keys', 'seed_nonce', schema='eth_private')
