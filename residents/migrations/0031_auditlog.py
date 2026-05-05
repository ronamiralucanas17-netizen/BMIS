import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('residents', '0030_resident_away_duration_months_and_more'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='AuditLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('actor_role', models.CharField(blank=True, max_length=20)),
                ('action', models.CharField(choices=[('REQUEST', 'Request'), ('LOGIN', 'Login'), ('LOGOUT', 'Logout'), ('CREATE', 'Create'), ('UPDATE', 'Update'), ('DELETE', 'Delete')], max_length=20)),
                ('object_type', models.CharField(blank=True, max_length=100)),
                ('object_id', models.CharField(blank=True, max_length=64)),
                ('object_repr', models.CharField(blank=True, max_length=255)),
                ('path', models.TextField(blank=True)),
                ('method', models.CharField(blank=True, max_length=10)),
                ('status_code', models.IntegerField(blank=True, null=True)),
                ('ip_address', models.GenericIPAddressField(blank=True, null=True)),
                ('user_agent', models.TextField(blank=True)),
                ('details', models.JSONField(blank=True, default=dict)),
                ('actor', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='audit_logs', to=settings.AUTH_USER_MODEL)),
                ('barangay', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='audit_logs', to='residents.barangay')),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='auditlog',
            index=models.Index(fields=['-created_at'], name='res_audit_created_at_idx'),
        ),
        migrations.AddIndex(
            model_name='auditlog',
            index=models.Index(fields=['barangay', '-created_at'], name='res_audit_brgy_created_idx'),
        ),
        migrations.AddIndex(
            model_name='auditlog',
            index=models.Index(fields=['actor', '-created_at'], name='res_audit_actor_created_idx'),
        ),
        migrations.AddIndex(
            model_name='auditlog',
            index=models.Index(fields=['action', '-created_at'], name='res_audit_action_created_idx'),
        ),
    ]
