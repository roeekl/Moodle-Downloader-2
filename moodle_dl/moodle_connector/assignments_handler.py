from typing import Dict, List
from moodle_dl.state_recorder.course import Course
from moodle_dl.moodle_connector.request_helper import RequestHelper


class AssignmentsHandler:
    """
    Fetches and parses the various endpoints in Moodle for assignment entries.
    """

    def __init__(self, request_helper: RequestHelper, version: int):
        self.request_helper = request_helper
        self.version = version

    def fetch_assignments(self, courses: List[Course]) -> Dict[int, Dict[int, Dict]]:
        """
        Fetches the Assignments List for all courses from the
        Moodle system
        @return: A Dictionary of all assignments,
                 indexed by courses, then assignment
        """
        # do this only if version is greater then 2.4
        # because mod_assign_get_assignments will fail
        if self.version < 2012120300:
            return {}

        print('\rDownloading assignments information\033[K', end='')

        # We create a dictionary with all the courses we want to request.
        extra_data = {}
        courseids = {}
        for index, course in enumerate(courses):
            courseids.update({str(index): course.id})

        extra_data.update({'courseids': courseids})

        assign_result = self.request_helper.post_REST('mod_assign_get_assignments', extra_data)

        assign_courses = assign_result.get('courses', [])

        result = {}
        for assign_course in assign_courses:
            course_id = assign_course.get('id', 0)
            course_assigns = {}
            course_assign_objs = assign_course.get('assignments', [])

            for course_assign_obj in course_assign_objs:
                assign_id = course_assign_obj.get('cmid', 0)
                assign_rid = course_assign_obj.get('id', 0)
                assign_name = course_assign_obj.get('name', '')
                assign_timemodified = course_assign_obj.get('timemodified', 0)
                assign_intro = course_assign_obj.get('intro', '')

                assign_files = []
                assign_files += course_assign_obj.get('introfiles', [])
                assign_files += course_assign_obj.get('introattachments', [])

                # normalize
                for assign_file in assign_files:
                    file_type = assign_file.get('type', '')
                    if file_type is None or file_type == '':
                        assign_file.update({'type': 'assign_file'})

                if assign_intro != '':
                    # Add intro file
                    intro_file = {
                        'filename': 'Assignment intro',
                        'filepath': '/',
                        'description': assign_intro,
                        'type': 'description',
                    }
                    assign_files.append(intro_file)

                course_assigns.update(
                    {
                        assign_id: {
                            'id': assign_rid,
                            'files': assign_files,
                            'name': assign_name,
                            'timemodified': assign_timemodified,
                        }
                    }
                )

            result.update({course_id: course_assigns})

        return result

    def fetch_submissions(self, userid: int, assignments: Dict[int, Dict[int, Dict]]) -> Dict[int, Dict[int, Dict]]:
        """
        Fetches for the assignments list of all courses the additionally
        submissions. This is kind of waste of resources, because there
        is no API to get all submissions at once
        @param userid: the user id.
        @param assignments: the dictionary of assignments of all courses.
        @return: A Dictionary of all assignments,
                 indexed by courses, then assignment
        """
        # do this only if version is greater then 3.1
        # because mod_assign_get_submission_status will fail
        if self.version < 2016052300:
            return assignments

        counter = 0
        total = 0

        # count total assignments for nice console output
        for course_id in assignments:
            for assignment_id in assignments[course_id]:
                total += 1

        for course_id in assignments:
            for assignment_id in assignments[course_id]:
                counter += 1
                assign = assignments[course_id][assignment_id]
                real_id = assign.get('id', 0)
                data = {'userid': userid, 'assignid': real_id}

                shorted_assign_name = assign.get('name', '')
                if len(shorted_assign_name) > 17:
                    shorted_assign_name = shorted_assign_name[:15] + '..'

                print(
                    (
                        '\r'
                        + 'Downloading submission information'
                        + f' {counter:3d}/{total:3d}'
                        + f' [{shorted_assign_name:<17}|{course_id:6}]\033[K'
                    ),
                    end='',
                )

                submission = self.request_helper.post_REST('mod_assign_get_submission_status', data)

                submission_files = self._get_files_of_submission(submission)
                assign['files'] += submission_files

        return assignments

    @staticmethod
    def _get_files_of_submission(submission: Dict) -> List:
        result = []
        # get own submissions
        lastattempt = submission.get('lastattempt', {})
        l_submission = lastattempt.get('submission', {})
        l_teamsubmission = lastattempt.get('teamsubmission', {})

        # get teachers feedback
        feedback = submission.get('feedback', {})

        result += AssignmentsHandler._get_files_of_plugins(l_submission)
        result += AssignmentsHandler._get_files_of_plugins(l_teamsubmission)
        result += AssignmentsHandler._get_files_of_plugins(feedback)
        result += AssignmentsHandler._get_grade_of_feedback(feedback)

        return result

    @staticmethod
    def _get_grade_of_feedback(feedback: Dict) -> List:
        result = []

        gradefordisplay = feedback.get('gradefordisplay', "")
        gradeddate = feedback.get('gradeddate', 0)
        if gradeddate is None or gradefordisplay is None or gradeddate == 0 or gradefordisplay == "":
            return result

        file = {
            'filename': 'grade',
            'filepath': '/',
            'timemodified': gradeddate,
            'description': gradefordisplay,
            'type': 'description',
        }

        result.append(file)

        return result

    @staticmethod
    def _get_files_of_plugins(obj: Dict) -> List:
        result = []
        plugins = obj.get('plugins', [])

        for plugin in plugins:
            fileareas = plugin.get('fileareas', [])

            for filearea in fileareas:
                files = filearea.get('files', [])

                for file in files:
                    file_type = file.get('type', '')
                    if file_type is None or file_type == '':
                        file.update({'type': 'submission_file'})

                    result.append(file)

        for plugin in plugins:
            editorfields = plugin.get('editorfields', [])

            for editorfield in editorfields:

                filename = editorfield.get('description', '')
                description = editorfield.get('text', '')
                if filename != '' and description != '':
                    description_file = {
                        'filename': filename,
                        'description': description,
                        'type': 'description',
                    }
                    result.append(description_file)

        return result
