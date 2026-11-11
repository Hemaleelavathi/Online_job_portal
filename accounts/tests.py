import tempfile

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from jobs.models import Job, JobApplication

from .models import UserProfile

User = get_user_model()


class RegistrationTests(TestCase):
    """Verify user registration validation, hashing, persistence, messages, and redirect."""

    def setUp(self):
        self.register_url = reverse('register')
        self.login_url = reverse('login')
        self.valid_payload = {
            'full_name': 'Alice Johnson',
            'email': 'Alice.Johnson@Example.com',
            'role': UserProfile.ROLE_JOB_SEEKER,
            'password': 'StrongPassword#2026',
            'confirm_password': 'StrongPassword#2026',
        }

    def test_register_page_renders_all_required_fields(self):
        response = self.client.get(self.register_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'accounts/register.html')
        self.assertTemplateUsed(response, 'base.html')

        for expected in (
            'Full Name',
            'Email Address',
            'User Role',
            'Job Seeker',
            'Employer',
            'Password',
            'Confirm Password',
        ):
            self.assertContains(response, expected)

    def test_successful_registration_hashes_password_saves_profile_and_redirects(self):
        response = self.client.post(self.register_url, self.valid_payload, follow=True)

        self.assertRedirects(response, self.login_url)
        self.assertContains(
            response,
            'Registration successful! You can now log in with your email and password.',
        )

        user = User.objects.get(email='alice.johnson@example.com')
        self.assertEqual(user.username, 'alice.johnson@example.com')
        self.assertEqual(user.first_name, 'Alice')
        self.assertEqual(user.last_name, 'Johnson')
        self.assertNotEqual(user.password, self.valid_payload['password'])
        self.assertTrue(user.has_usable_password())
        self.assertTrue(user.check_password(self.valid_payload['password']))

        self.assertEqual(user.profile.full_name, 'Alice Johnson')
        self.assertEqual(user.profile.role, UserProfile.ROLE_JOB_SEEKER)

    def test_employer_registration_saves_employer_role(self):
        payload = {
            **self.valid_payload,
            'full_name': 'Bob Smith',
            'email': 'bob@company.com',
            'role': UserProfile.ROLE_EMPLOYER,
        }
        response = self.client.post(self.register_url, payload)
        self.assertEqual(response.status_code, 302)

        user = User.objects.get(email='bob@company.com')
        self.assertEqual(user.profile.role, UserProfile.ROLE_EMPLOYER)

    def test_duplicate_email_is_rejected_case_insensitively(self):
        self.client.post(self.register_url, self.valid_payload)

        duplicate_payload = {
            **self.valid_payload,
            'full_name': 'Another User',
            'email': 'ALICE.JOHNSON@example.com',
        }
        response = self.client.post(self.register_url, duplicate_payload)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'An account with this email address already exists.')
        self.assertContains(response, 'Please correct the errors highlighted below.')
        self.assertEqual(User.objects.count(), 1)
        self.assertEqual(UserProfile.objects.count(), 1)

    def test_password_mismatch_fails_validation(self):
        payload = {
            **self.valid_payload,
            'confirm_password': 'DifferentPassword#2026',
        }
        response = self.client.post(self.register_url, payload)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Passwords do not match.')
        self.assertEqual(User.objects.count(), 0)

    def test_weak_password_fails_django_password_validation(self):
        payload = {
            **self.valid_payload,
            'password': '123456',
            'confirm_password': '123456',
        }
        response = self.client.post(self.register_url, payload)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Please correct the errors highlighted below.')
        self.assertEqual(User.objects.count(), 0)

    def test_missing_fields_and_invalid_role_fail_validation(self):
        payload = {
            'full_name': ' ',
            'email': 'not-an-email',
            'role': 'admin',
            'password': '',
            'confirm_password': '',
        }
        response = self.client.post(self.register_url, payload)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Please correct the errors highlighted below.')
        self.assertEqual(User.objects.count(), 0)


class AuthenticationAndDashboardTests(TestCase):
    """Verify email/password login, role redirects, protected dashboards, sessions, and logout."""

    def setUp(self):
        self.login_url = reverse('login')
        self.logout_url = reverse('logout')
        self.register_url = reverse('register')
        self.dashboard_url = reverse('dashboard')
        self.seeker_dashboard_url = reverse('job_seeker_dashboard')
        self.employer_dashboard_url = reverse('employer_dashboard')

        self.password = 'SecurePass#2026'
        self.seeker_user = self._create_account(
            email='seeker@example.com',
            full_name='Jane Seeker',
            role=UserProfile.ROLE_JOB_SEEKER,
        )
        self.employer_user = self._create_account(
            email='employer@example.com',
            full_name='Acme Corp',
            role=UserProfile.ROLE_EMPLOYER,
        )

    def _create_account(self, email, full_name, role):
        user = User.objects.create_user(
            username=email,
            email=email,
            password=self.password,
            first_name=full_name.split()[0],
            last_name=full_name.split()[1] if len(full_name.split()) > 1 else '',
        )
        UserProfile.objects.create(user=user, full_name=full_name, role=role)
        return user

    def test_login_page_renders_email_and_password_fields(self):
        response = self.client.get(self.login_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'accounts/login.html')
        self.assertContains(response, 'Email Address')
        self.assertContains(response, 'Password')
        self.assertContains(response, 'Sign In')

    def test_job_seeker_login_redirects_maintains_session_and_logs_out(self):
        response = self.client.post(
            self.login_url,
            {'email': 'SEEKER@example.com', 'password': self.password},
            follow=True,
        )

        self.assertRedirects(response, self.seeker_dashboard_url)
        self.assertContains(response, 'Job Seeker Dashboard')
        self.assertContains(response, 'Welcome back, Jane Seeker!')
        self.assertIn('_auth_user_id', self.client.session)

        home_response = self.client.get(reverse('home'))
        self.assertContains(home_response, 'Jane Seeker')
        self.assertContains(home_response, 'Logout')

        logout_response = self.client.post(self.logout_url, follow=True)
        self.assertRedirects(logout_response, self.login_url)
        self.assertContains(logout_response, 'You have been logged out successfully.')
        self.assertNotIn('_auth_user_id', self.client.session)

        protected_after_logout = self.client.get(self.seeker_dashboard_url)
        self.assertRedirects(
            protected_after_logout,
            f'{self.login_url}?next={self.seeker_dashboard_url}',
        )

    def test_employer_login_redirects_maintains_session_and_logs_out(self):
        response = self.client.post(
            self.login_url,
            {'email': 'employer@example.com', 'password': self.password},
            follow=True,
        )

        self.assertRedirects(response, self.employer_dashboard_url)
        self.assertContains(response, 'Employer Dashboard')
        self.assertContains(response, 'Welcome back, Acme Corp!')
        self.assertIn('_auth_user_id', self.client.session)

        dashboard_response = self.client.get(self.dashboard_url)
        self.assertRedirects(dashboard_response, self.employer_dashboard_url)

        logout_response = self.client.post(self.logout_url, follow=True)
        self.assertRedirects(logout_response, self.login_url)
        self.assertContains(logout_response, 'You have been logged out successfully.')
        self.assertNotIn('_auth_user_id', self.client.session)

        protected_after_logout = self.client.get(self.employer_dashboard_url)
        self.assertRedirects(
            protected_after_logout,
            f'{self.login_url}?next={self.employer_dashboard_url}',
        )

    def test_invalid_credentials_show_error_and_do_not_login(self):
        for email, password in (
            ('seeker@example.com', 'WrongPassword123'),
            ('missing@example.com', self.password),
        ):
            response = self.client.post(
                self.login_url,
                {'email': email, 'password': password},
            )
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, 'Invalid email address or password.')
            self.assertNotIn('_auth_user_id', self.client.session)

    def test_inactive_user_cannot_login(self):
        self.seeker_user.is_active = False
        self.seeker_user.save()

        response = self.client.post(
            self.login_url,
            {'email': 'seeker@example.com', 'password': self.password},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Invalid email address or password.')
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_unauthenticated_users_cannot_access_dashboards(self):
        for url in (self.dashboard_url, self.seeker_dashboard_url, self.employer_dashboard_url):
            response = self.client.get(url)
            self.assertRedirects(response, f'{self.login_url}?next={url}')

    def test_cross_role_dashboard_access_is_forbidden(self):
        self.client.post(
            self.login_url,
            {'email': 'seeker@example.com', 'password': self.password},
        )
        employer_page = self.client.get(self.employer_dashboard_url)
        self.assertEqual(employer_page.status_code, 403)
        self.assertContains(employer_page, 'Access Restricted', status_code=403)

        self.client.post(self.logout_url)

        self.client.post(
            self.login_url,
            {'email': 'employer@example.com', 'password': self.password},
        )
        seeker_page = self.client.get(self.seeker_dashboard_url)
        self.assertEqual(seeker_page.status_code, 403)
        self.assertContains(seeker_page, 'Access Restricted', status_code=403)

    def test_logout_requires_post(self):
        self.client.post(
            self.login_url,
            {'email': 'seeker@example.com', 'password': self.password},
        )
        response = self.client.get(self.logout_url)
        self.assertEqual(response.status_code, 405)
        self.assertIn('_auth_user_id', self.client.session)

    def test_authenticated_user_redirected_from_login_and_register(self):
        self.client.post(
            self.login_url,
            {'email': 'employer@example.com', 'password': self.password},
        )
        self.assertRedirects(self.client.get(self.login_url), self.employer_dashboard_url)
        self.assertRedirects(self.client.get(self.register_url), self.employer_dashboard_url)


class JobSeekerDashboardTests(TestCase):
    """Verify Job Seeker dashboard content, profile updates, PDF resume upload, job applications, and access control."""

    def setUp(self):
        self.login_url = reverse('login')
        self.logout_url = reverse('logout')
        self.dashboard_url = reverse('job_seeker_dashboard')
        self.password = 'SecurePass#2026'

        self.seeker_user = User.objects.create_user(
            username='seeker@example.com',
            email='seeker@example.com',
            password=self.password,
            first_name='Jane',
            last_name='Seeker',
        )
        self.seeker_profile = UserProfile.objects.create(
            user=self.seeker_user,
            full_name='Jane Seeker',
            role=UserProfile.ROLE_JOB_SEEKER,
        )

        self.employer_user = User.objects.create_user(
            username='employer@example.com',
            email='employer@example.com',
            password=self.password,
            first_name='Acme',
            last_name='Corp',
        )
        UserProfile.objects.create(
            user=self.employer_user,
            full_name='Acme Corp',
            role=UserProfile.ROLE_EMPLOYER,
        )

        self.sample_job = Job.objects.first()

    def _login_seeker(self):
        self.client.post(
            self.login_url,
            {'email': 'seeker@example.com', 'password': self.password},
        )

    def test_dashboard_displays_welcome_profile_jobs_and_logout(self):
        self._login_seeker()
        response = self.client.get(self.dashboard_url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'accounts/job_seeker_dashboard.html')
        for expected in (
            'Welcome, Jane Seeker!',
            'Profile Information',
            'seeker@example.com',
            'Update Profile',
            'Highest Qualification',
            'Skills',
            'Resume (PDF only)',
            'Available Jobs',
            'Applied Jobs',
            self.sample_job.title,
            'Logout',
        ):
            self.assertContains(response, expected)

    def test_job_seeker_can_update_profile_and_upload_pdf_resume(self):
        self._login_seeker()
        valid_pdf = SimpleUploadedFile(
            'jane_resume.pdf',
            b'%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\n%%EOF',
            content_type='application/pdf',
        )

        with tempfile.TemporaryDirectory() as media_dir:
            with override_settings(MEDIA_ROOT=media_dir):
                response = self.client.post(
                    self.dashboard_url,
                    {
                        'full_name': 'Jane Doe',
                        'phone': '+91 98765 43210',
                        'location': 'Bengaluru, IN',
                        'qualification': 'B.Tech in Computer Science',
                        'skills': 'Python, Django, SQL',
                        'resume': valid_pdf,
                    },
                    follow=True,
                )

                self.assertRedirects(response, self.dashboard_url)
                self.assertContains(response, 'Your profile has been updated successfully.')
                self.assertContains(response, 'Welcome, Jane Doe!')
                self.assertContains(response, 'B.Tech in Computer Science')
                self.assertContains(response, 'Python')
                self.assertContains(response, 'Django')
                self.assertContains(response, 'View PDF')

                self.seeker_profile.refresh_from_db()
                self.seeker_user.refresh_from_db()
                self.assertEqual(self.seeker_profile.full_name, 'Jane Doe')
                self.assertEqual(self.seeker_user.first_name, 'Jane')
                self.assertEqual(self.seeker_user.last_name, 'Doe')
                self.assertEqual(self.seeker_profile.qualification, 'B.Tech in Computer Science')
                self.assertEqual(self.seeker_profile.skills, 'Python, Django, SQL')
                self.assertTrue(self.seeker_profile.resume.name.startswith('resumes/'))
                self.assertTrue(self.seeker_profile.resume.name.endswith('.pdf'))

    def test_non_pdf_resume_upload_is_rejected(self):
        self._login_seeker()

        for filename, content, content_type, expected_error in (
            ('resume.txt', b'Plain text resume', 'text/plain', 'Only PDF files (.pdf) are allowed.'),
            ('fake.pdf', b'Not really a PDF', 'application/pdf', 'The uploaded file is not a valid PDF document.'),
        ):
            bad_file = SimpleUploadedFile(filename, content, content_type=content_type)
            response = self.client.post(
                self.dashboard_url,
                {
                    'full_name': 'Jane Seeker',
                    'qualification': 'MCA',
                    'skills': 'Python',
                    'resume': bad_file,
                },
            )
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, expected_error)
            self.seeker_profile.refresh_from_db()
            self.assertFalse(bool(self.seeker_profile.resume))

    def test_job_seeker_can_apply_and_view_applied_jobs(self):
        self._login_seeker()
        apply_url = reverse('apply_to_job', args=[self.sample_job.id])

        response = self.client.post(apply_url, follow=True)
        self.assertRedirects(response, self.dashboard_url)
        self.assertContains(
            response,
            f'Application submitted for {self.sample_job.title} at {self.sample_job.company}.',
        )
        self.assertEqual(
            JobApplication.objects.filter(job=self.sample_job, applicant=self.seeker_user).count(),
            1,
        )
        self.assertContains(response, '1 Total')

        duplicate_response = self.client.post(apply_url, follow=True)
        self.assertContains(
            duplicate_response,
            f'You have already applied for {self.sample_job.title} at {self.sample_job.company}.',
        )
        self.assertEqual(
            JobApplication.objects.filter(job=self.sample_job, applicant=self.seeker_user).count(),
            1,
        )

    def test_only_job_seekers_can_access_dashboard_and_apply(self):
        apply_url = reverse('apply_to_job', args=[self.sample_job.id])

        self.assertRedirects(self.client.get(self.dashboard_url), f'{self.login_url}?next={self.dashboard_url}')
        self.assertRedirects(self.client.post(apply_url), f'{self.login_url}?next={apply_url}')

        self.client.post(
            self.login_url,
            {'email': 'employer@example.com', 'password': self.password},
        )
        self.assertEqual(self.client.get(self.dashboard_url).status_code, 403)
        self.assertEqual(self.client.post(apply_url).status_code, 403)
        self.assertEqual(JobApplication.objects.count(), 0)


class EmployerDashboardTests(TestCase):
    """Verify Employer dashboard, company updates, job CRUD, applicants view, and ownership protection."""

    def setUp(self):
        self.login_url = reverse('login')
        self.dashboard_url = reverse('employer_dashboard')
        self.create_job_url = reverse('create_job')
        self.password = 'SecurePass#2026'

        self.employer_a = User.objects.create_user(
            username='emp_a@example.com',
            email='emp_a@example.com',
            password=self.password,
            first_name='Alice',
            last_name='Recruiter',
        )
        self.profile_a = UserProfile.objects.create(
            user=self.employer_a,
            full_name='Alice Recruiter',
            role=UserProfile.ROLE_EMPLOYER,
            company_name='Alpha Tech',
            company_description='Building cloud software.',
        )

        self.employer_b = User.objects.create_user(
            username='emp_b@example.com',
            email='emp_b@example.com',
            password=self.password,
            first_name='Bob',
            last_name='Hiring',
        )
        self.profile_b = UserProfile.objects.create(
            user=self.employer_b,
            full_name='Bob Hiring',
            role=UserProfile.ROLE_EMPLOYER,
            company_name='Beta Corp',
        )

        self.seeker_user = User.objects.create_user(
            username='candidate@example.com',
            email='candidate@example.com',
            password=self.password,
            first_name='Sam',
            last_name='Candidate',
        )
        self.seeker_profile = UserProfile.objects.create(
            user=self.seeker_user,
            full_name='Sam Candidate',
            role=UserProfile.ROLE_JOB_SEEKER,
            qualification='M.Sc. Computer Science',
            skills='Python, Django, SQL',
        )

        self.job_a = Job.objects.create(
            title='Platform Engineer',
            company='Alpha Tech',
            location='Remote',
            job_type=Job.JOB_TYPE_REMOTE,
            salary='$95k - $120k',
            skills_required='Python, Django',
            description='Develop backend platform APIs and services.',
            employer=self.employer_a,
        )
        self.job_b = Job.objects.create(
            title='Secret Beta Role',
            company='Beta Corp',
            location='Delhi, IN',
            job_type=Job.JOB_TYPE_FULL_TIME,
            salary='$70k - $90k',
            skills_required='Java, Spring',
            description='Internal engineering position at Beta Corp.',
            employer=self.employer_b,
        )

    def _login_as(self, email):
        self.client.post(self.login_url, {'email': email, 'password': self.password})

    def test_employer_dashboard_displays_name_company_jobs_and_post_option(self):
        self._login_as('emp_a@example.com')
        response = self.client.get(self.dashboard_url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'accounts/employer_dashboard.html')
        for expected in (
            'Welcome, Alice Recruiter!',
            'Company Details',
            'Alpha Tech',
            'Building cloud software.',
            'Update Company Details',
            'Post New Job',
            'Platform Engineer',
            'Applicants for Your Jobs',
        ):
            self.assertContains(response, expected)

        self.assertNotContains(response, 'Secret Beta Role')

    def test_employer_can_update_company_details(self):
        self._login_as('emp_a@example.com')
        response = self.client.post(
            self.dashboard_url,
            {
                'full_name': 'Alice Morgan',
                'company_name': 'Alpha Cloud Labs',
                'company_description': 'Modern developer tooling and AI platforms.',
                'location': 'Bengaluru, IN',
                'phone': '+91 90000 11111',
            },
            follow=True,
        )

        self.assertRedirects(response, self.dashboard_url)
        self.assertContains(response, 'Company details updated successfully.')
        self.assertContains(response, 'Welcome, Alice Morgan!')
        self.assertContains(response, 'Alpha Cloud Labs')
        self.assertContains(response, 'Modern developer tooling and AI platforms.')

        self.profile_a.refresh_from_db()
        self.employer_a.refresh_from_db()
        self.assertEqual(self.profile_a.full_name, 'Alice Morgan')
        self.assertEqual(self.employer_a.first_name, 'Alice')
        self.assertEqual(self.employer_a.last_name, 'Morgan')
        self.assertEqual(self.profile_a.company_name, 'Alpha Cloud Labs')
        self.assertEqual(self.profile_a.company_description, 'Modern developer tooling and AI platforms.')

    def test_employer_can_post_edit_and_delete_own_job(self):
        self._login_as('emp_a@example.com')

        create_get = self.client.get(self.create_job_url)
        self.assertEqual(create_get.status_code, 200)
        self.assertContains(create_get, 'Alpha Tech')

        create_post = self.client.post(
            self.create_job_url,
            {
                'title': 'Django Tech Lead',
                'company': 'Alpha Tech',
                'location': 'Hyderabad, IN',
                'job_type': Job.JOB_TYPE_HYBRID,
                'salary': '$110k - $135k',
                'experience': '3-5 years',
                'skills_required': 'Python, Django, AWS',
                'description': 'Lead architecture and mentor backend engineers.',
                'is_active': 'on',
            },
            follow=True,
        )
        self.assertRedirects(create_post, self.dashboard_url)
        self.assertContains(create_post, 'Job &quot;Django Tech Lead&quot; posted successfully.')
        self.assertContains(create_post, 'Django Tech Lead')

        created_job = Job.objects.get(title='Django Tech Lead')
        self.assertEqual(created_job.employer, self.employer_a)

        edit_url = reverse('edit_job', args=[created_job.id])
        edit_post = self.client.post(
            edit_url,
            {
                'title': 'Principal Django Engineer',
                'company': 'Alpha Tech',
                'location': 'Remote',
                'job_type': Job.JOB_TYPE_REMOTE,
                'salary': '$120k - $145k',
                'experience': '5+ years',
                'skills_required': 'Python, Django, PostgreSQL',
                'description': 'Architect high-throughput web APIs and mentoring.',
                'is_active': 'on',
            },
            follow=True,
        )
        self.assertRedirects(edit_post, self.dashboard_url)
        self.assertContains(edit_post, 'Job &quot;Principal Django Engineer&quot; updated successfully.')
        created_job.refresh_from_db()
        self.assertEqual(created_job.title, 'Principal Django Engineer')
        self.assertEqual(created_job.location, 'Remote')

        delete_url = reverse('delete_job', args=[created_job.id])
        delete_get = self.client.get(delete_url)
        self.assertEqual(delete_get.status_code, 200)
        self.assertContains(delete_get, 'Delete Job Posting?')

        delete_post = self.client.post(delete_url, follow=True)
        self.assertRedirects(delete_post, self.dashboard_url)
        self.assertContains(delete_post, 'Job &quot;Principal Django Engineer&quot; deleted successfully.')
        self.assertFalse(Job.objects.filter(pk=created_job.id).exists())

    def test_employer_sees_applicants_only_for_own_jobs(self):
        with tempfile.TemporaryDirectory() as media_dir:
            with override_settings(MEDIA_ROOT=media_dir):
                self.seeker_profile.resume = SimpleUploadedFile(
                    'sam_cv.pdf',
                    b'%PDF-1.4\n%resume\n%%EOF',
                    content_type='application/pdf',
                )
                self.seeker_profile.save()

                JobApplication.objects.create(job=self.job_a, applicant=self.seeker_user)
                JobApplication.objects.create(job=self.job_b, applicant=self.seeker_user)

                self._login_as('emp_a@example.com')
                response = self.client.get(self.dashboard_url)

                self.assertEqual(response.status_code, 200)
                self.assertContains(response, 'Sam Candidate')
                self.assertContains(response, 'candidate@example.com')
                self.assertContains(response, 'M.Sc. Computer Science')
                self.assertContains(response, 'Platform Engineer')
                self.assertContains(response, 'View Resume')
                self.assertNotContains(response, 'Secret Beta Role')

                filtered = self.client.get(f'{self.dashboard_url}?job={self.job_a.id}')
                self.assertEqual(filtered.status_code, 200)
                self.assertContains(filtered, 'Filtered by:')

    def test_employer_cannot_manage_or_filter_another_employers_jobs(self):
        self._login_as('emp_a@example.com')

        edit_other = reverse('edit_job', args=[self.job_b.id])
        delete_other = reverse('delete_job', args=[self.job_b.id])
        seeded_job = Job.objects.filter(employer__isnull=True).first()

        self.assertEqual(self.client.get(edit_other).status_code, 403)
        self.assertEqual(self.client.post(edit_other, {'title': 'Hacked'}).status_code, 403)
        self.assertEqual(self.client.get(delete_other).status_code, 403)
        self.assertEqual(self.client.post(delete_other).status_code, 403)
        self.assertEqual(self.client.get(f'{self.dashboard_url}?job={self.job_b.id}').status_code, 403)

        if seeded_job:
            self.assertEqual(self.client.get(reverse('edit_job', args=[seeded_job.id])).status_code, 403)
            self.assertEqual(self.client.post(reverse('delete_job', args=[seeded_job.id])).status_code, 403)

        self.job_b.refresh_from_db()
        self.assertEqual(self.job_b.title, 'Secret Beta Role')

    def test_job_seekers_and_anonymous_cannot_access_employer_job_management(self):
        edit_url = reverse('edit_job', args=[self.job_a.id])
        delete_url = reverse('delete_job', args=[self.job_a.id])

        for url in (self.dashboard_url, self.create_job_url, edit_url, delete_url):
            self.assertRedirects(self.client.get(url), f'{self.login_url}?next={url}')

        self._login_as('candidate@example.com')
        for url in (self.dashboard_url, self.create_job_url, edit_url, delete_url):
            self.assertEqual(self.client.get(url).status_code, 403)
