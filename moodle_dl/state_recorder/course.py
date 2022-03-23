from typing import List
from moodle_dl.state_recorder.file import File
from moodle_dl.download_service.path_tools import PathTools


class Course:
    def __init__(self, _id: int, fullname: str, files: List[File] = None):
        self.id = _id
        self.fullname = PathTools.to_valid_name(fullname)
        if files is not None:
            self.files = files
        else:
            self.files = []

        self.overwrite_name_with = None
        self.create_directory_structure = True
        self.excluded_sections = []

    def __str__(self):
        message = 'Course ('

        message += 'id: %s' % (self.id)
        message += ', fullname: "%s"' % (self.fullname)
        message += ', overwrite_name_with: "%s"' % (PathTools.to_valid_name(self.overwrite_name_with))
        message += ', create_directory_structure: %s' % (self.create_directory_structure)
        message += ', files: %s' % (len(self.files))

        # for i, file in enumerate(self.files):
        #     message += ', file[%i]: %s' % (i, file)

        message += ')'
        return message
