import cloudinary
import cloudinary.api
import cloudinary.uploader
import cloudinary.utils

from pathlib import PurePosixPath
from urllib.request import urlopen

from django.conf import settings
from django.core.files import File
from django.core.files.base import ContentFile
from django.core.files.storage import Storage


class CloudinaryMediaStorage(Storage):
    """
    Store uploaded media files in Cloudinary.
    Django keeps the original relative filename in the database.
    """

    def _configure(self):
        cloudinary.config(
            cloud_name=settings.CLOUDINARY_CLOUD_NAME,
            api_key=settings.CLOUDINARY_API_KEY,
            api_secret=settings.CLOUDINARY_API_SECRET,
            secure=True,
        )

    @staticmethod
    def _public_id(name):
        path = PurePosixPath(str(name).replace("\\", "/"))
        return str(path.with_suffix(""))

    def _save(self, name, content):
        self._configure()

        if hasattr(content, "seek"):
            content.seek(0)

        cloudinary.uploader.upload(
            content,
            public_id=self._public_id(name),
            resource_type="image",
            overwrite=False,
            unique_filename=False,
            use_filename=False,
        )

        return str(name).replace("\\", "/")

    def exists(self, name):
        self._configure()

        try:
            cloudinary.api.resource(
                self._public_id(name),
                resource_type="image",
            )
            return True
        except Exception as exc:
            if getattr(exc, "http_code", None) == 404:
                return False
            raise

    def url(self, name):
        self._configure()

        path = PurePosixPath(str(name).replace("\\", "/"))
        extension = path.suffix.lstrip(".").lower() or None

        url, _ = cloudinary.utils.cloudinary_url(
            self._public_id(name),
            secure=True,
            resource_type="image",
            format=extension,
        )
        return url

    def delete(self, name):
        self._configure()

        cloudinary.uploader.destroy(
            self._public_id(name),
            resource_type="image",
            invalidate=True,
        )

    def size(self, name):
        self._configure()

        result = cloudinary.api.resource(
            self._public_id(name),
            resource_type="image",
        )
        return result["bytes"]

    def _open(self, name, mode="rb"):
        if mode != "rb":
            raise ValueError(
                "Cloudinary storage supports read-only access."
            )

        with urlopen(self.url(name)) as response:
            content = ContentFile(response.read(), name=name)

        return File(content, name=name)

    def path(self, name):
        raise NotImplementedError(
            "Cloudinary files do not have a local filesystem path."
        )
