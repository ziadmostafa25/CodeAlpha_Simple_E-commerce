from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator

MAX_IMAGE_SIZE_MB = 5


def validate_image_size(file):
    if file.size > MAX_IMAGE_SIZE_MB * 1024 * 1024:
        raise ValidationError(f'Images must be {MAX_IMAGE_SIZE_MB} MB or smaller.')


# Used on every image upload field. Pillow still verifies the file is a real image.
IMAGE_VALIDATORS = [
    FileExtensionValidator(['jpg', 'jpeg', 'png', 'webp']),
    validate_image_size,
]
