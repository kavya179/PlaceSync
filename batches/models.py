from django.db import models

class Batch(models.Model):
    department = models.ForeignKey(
        'departments.Department', 
        on_delete=models.CASCADE, 
        related_name='batches'
    )
    name = models.CharField(
        max_length=255, 
        help_text="e.g. 2027 Information Technology"
    )
    graduation_year = models.PositiveIntegerField(
        help_text="e.g. 2027"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['department', 'name'], 
                name='unique_department_batch_name'
            ),
        ]
        ordering = ['-graduation_year', 'name']

    def __str__(self):
        return f"{self.name} ({self.department.code})"
