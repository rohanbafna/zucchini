import json
from fractions import Fraction

from ..submission import BrokenSubmissionError
from ..utils import run_process, PIPE, STDOUT, TimeoutExpired
from ..grades import PartGrade
from . import GraderInterface, Part

"""
Grade a homework using the classic Java bitwise operators grader
(usually homework 2).
"""


class CircuitSimTest(Part):
    __slots__ = ('test',)

    def __init__(self, test):
        self.test = test

    def description(self):
        return self.test

    def grade(self, results):
        test_results = [result for result in results
                        if result['methodName'] == self.test]

        if not test_results:
            return PartGrade(score=Fraction(0),
                             log='results for test not found')

        log = '\n'.join('{0[displayName]}: {0[message]}'.format(test_result)
                        for test_result in test_results
                        if not test_result['passed'])

        score = Fraction(sum(1 for test_result in test_results
                             if test_result['passed']),
                         len(test_results))
        return PartGrade(score=score, log=log)


class CircuitSimGrader(GraderInterface):
    """
    Run a CircuitSim grader based on
    <https://github.com/ausbin/circuitsim-grader-template> and collect
    the results.
    """

    DEFAULT_TIMEOUT = 30

    def __init__(self, grader_jar, test_class, timeout=None):
        self.grader_jar = grader_jar
        self.test_class = test_class

        if timeout is None:
            self.timeout = self.DEFAULT_TIMEOUT
        else:
            self.timeout = timeout

    def list_prerequisites(self):
        return ['sudo apt-get install openjdk-8-jre-headless']

    def part_from_config_dict(self, config_dict):
        return CircuitSimTest.from_config_dict(config_dict)

    def grade(self, submission, path, parts):
        cmdline = ['java', '-jar', self.grader_jar, '--zucchini',
                   self.test_class]
        try:
            process = run_process(cmdline, cwd=path, timeout=self.timeout,
                                  stdout=PIPE, stderr=STDOUT, input='')
        except TimeoutExpired:
            raise BrokenSubmissionError('timeout of {} seconds expired for '
                                        'grader'.format(self.timeout))

        if process.returncode != 0:
            raise BrokenSubmissionError(
                'grader command exited with nonzero exit code {}'
                .format(process.returncode),
                verbose=process.stdout.decode() if process.stdout else None)

        results = json.loads(process.stdout.decode())

        if 'error' in results:
            raise BrokenSubmissionError(results['error'])

        return [part.grade(results['tests']) for part in parts]