"""btc. add encryption to masterkey

Revision ID: e2f73f2ac60a
Revises: 
Create Date: 2018-02-15 01:28:44.325289

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e2f73f2ac60a'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column('master_keys', 'priv_masterkey', schema='btc_private', new_column_name='priv_masterkey_encrypted',
                    type_=sa.String(222))
    op.add_column('master_keys', sa.Column('priv_masterkey_aet', sa.String(32), unique=True), schema='btc_private')
    op.add_column('master_keys', sa.Column('priv_masterkey_nonce', sa.String(32), unique=True), schema='btc_private')


def downgrade():
    op.alter_column('master_keys', 'priv_masterkey_encrypted', schema='btc_private', new_column_name='priv_masterkey',
                    type_=sa.String(111))
    op.drop_column('master_keys', 'priv_masterkey_aet', schema='btc_private')
    op.drop_column('master_keys', 'priv_masterkey_nonce', schema='btc_private')
