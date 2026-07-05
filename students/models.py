from django.db import models
from django.conf import settings

class Student(models.Model):
    class PlacementStatus(models.TextChoices):
        UNPLACED = 'UNPLACED', 'Unplaced'
        PLACED = 'PLACED', 'Placed'
        INTERN = 'INTERN', 'Internship'
        PLACED_AND_INTERN = 'PLACED_AND_INTERN', 'Placed & Internship'

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='student_profile', 
        null=True, 
        blank=True
    )
    college = models.ForeignKey(
        'colleges.College', 
        on_delete=models.CASCADE, 
        related_name='students'
    )
    department = models.ForeignKey(
        'departments.Department', 
        on_delete=models.CASCADE, 
        related_name='students'
    )
    batch = models.ForeignKey(
        'batches.Batch', 
        on_delete=models.CASCADE, 
        related_name='students'
    )
    
    roll_number = models.CharField(max_length=50)
    name = models.CharField(max_length=255)
    email = models.EmailField()
    phone = models.CharField(max_length=20, blank=True)
    cgpa = models.DecimalField(
        max_digits=4, 
        decimal_places=2, 
        null=True, 
        blank=True, 
        help_text="CGPA out of 10"
    )
    backlogs = models.PositiveIntegerField(
        default=0,
        help_text="Number of active backlogs"
    )
    
    placement_status = models.CharField(
        max_length=20,
        choices=PlacementStatus.choices,
        default=PlacementStatus.UNPLACED
    )
    package_amount = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        null=True, 
        blank=True, 
        help_text="LPA package amount if placed"
    )
    stipend_amount = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        null=True, 
        blank=True, 
        help_text="Monthly stipend amount if doing internship"
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['college', 'roll_number'], 
                name='unique_college_roll_number'
            ),
        ]
        ordering = ['roll_number']

    def __str__(self):
        return f"{self.name} ({self.roll_number}) - {self.batch.name}"
