from django.contrib.staticfiles import finders
from django.test import TestCase
from django.urls import reverse


class HomePageTests(TestCase):
    """Verify the CareerConnect home page view, templates, static assets, and search."""

    def test_home_page_renders_required_sections(self):
        response = self.client.get(reverse('home'))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'home.html')
        self.assertTemplateUsed(response, 'base.html')

        for expected in (
            'CareerConnect',
            'Home',
            'Find Jobs',
            'Login',
            'Register',
            'Find Your Dream Job',
            'Featured Jobs',
            'Python / Django Developer',
            'All rights reserved.',
            'bootstrap@5.3.3',
            '/static/css/style.css',
        ):
            self.assertContains(response, expected)

    def test_static_css_exists(self):
        self.assertIsNotNone(finders.find('css/style.css'))

    def test_home_page_search_filters_featured_jobs(self):
        response = self.client.get(reverse('home'), {'q': 'Django'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Python / Django Developer')
        self.assertNotContains(response, 'Product Designer')

    def test_home_page_location_filter(self):
        response = self.client.get(reverse('home'), {'location': 'Remote'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Frontend UI/UX Engineer')
        self.assertNotContains(response, 'Cloud DevOps Specialist')

    def test_home_page_no_results_state(self):
        response = self.client.get(reverse('home'), {'q': 'NonexistentSkill123'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'No matching jobs found')


from django.contrib.auth import get_user_model
from accounts.models import UserProfile
from .models import Job

User = get_user_model()


class JobPostingModuleTests(TestCase):
    """Verify the Job model fields, validation, active jobs listing, detail view, and CRUD workflow."""

    def setUp(self):
        self.login_url = reverse('login')
        self.job_list_url = reverse('job_list')
        self.create_job_url = reverse('create_job')
        self.employer_dashboard_url = reverse('employer_dashboard')
        self.password = 'SecurePass#2026'

        self.employer = User.objects.create_user(
            username='emp@example.com',
            email='emp@example.com',
            password=self.password,
            first_name='Clara',
            last_name='Employer',
        )
        UserProfile.objects.create(
            user=self.employer,
            full_name='Clara Employer',
            role=UserProfile.ROLE_EMPLOYER,
            company_name='FutureTech Inc',
        )

        self.other_employer = User.objects.create_user(
            username='other@example.com',
            email='other@example.com',
            password=self.password,
            first_name='Dan',
            last_name='Other',
        )
        UserProfile.objects.create(
            user=self.other_employer,
            full_name='Dan Other',
            role=UserProfile.ROLE_EMPLOYER,
            company_name='OtherCo',
        )

        self.seeker = User.objects.create_user(
            username='seeker@example.com',
            email='seeker@example.com',
            password=self.password,
            first_name='Eve',
            last_name='Seeker',
        )
        UserProfile.objects.create(
            user=self.seeker,
            full_name='Eve Seeker',
            role=UserProfile.ROLE_JOB_SEEKER,
        )

    def _login(self, email):
        self.client.post(self.login_url, {'email': email, 'password': self.password})

    def test_job_model_exposes_all_required_fields(self):
        expected_fields = {
            'title',
            'company',
            'description',
            'location',
            'salary',
            'job_type',
            'skills_required',
            'experience',
            'posted_date',
            'employer',
        }
        model_fields = {field.name for field in Job._meta.get_fields()}
        self.assertTrue(expected_fields.issubset(model_fields))

    def test_job_posting_form_validation_rejects_invalid_inputs(self):
        self._login('emp@example.com')
        response = self.client.post(
            self.create_job_url,
            {
                'title': 'A',
                'company': '',
                'location': 'X',
                'job_type': 'InvalidType',
                'salary': '',
                'experience': '',
                'skills_required': ' , ',
                'description': 'Short',
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Please correct the errors in the job form below.')
        self.assertContains(response, 'Please enter a valid job title (at least 2 characters).')
        self.assertContains(response, 'Please enter a job description (at least 10 characters).')
        self.assertFalse(Job.objects.filter(employer=self.employer).exists())

    def test_only_authenticated_employers_can_post_jobs(self):
        self.assertRedirects(
            self.client.get(self.create_job_url),
            f'{self.login_url}?next={self.create_job_url}',
        )

        self._login('seeker@example.com')
        self.assertEqual(self.client.get(self.create_job_url).status_code, 403)
        self.assertEqual(
            self.client.post(
                self.create_job_url,
                {
                    'title': 'Blocked Job',
                    'company': 'Test',
                    'location': 'Remote',
                    'job_type': Job.JOB_TYPE_REMOTE,
                    'salary': '$50k',
                    'experience': '1 year',
                    'skills_required': 'Python',
                    'description': 'Should not be created by job seekers.',
                    'is_active': 'on',
                },
            ).status_code,
            403,
        )

    def test_complete_job_posting_edit_active_listing_and_delete_workflow(self):
        self._login('emp@example.com')

        create_response = self.client.post(
            self.create_job_url,
            {
                'title': 'Full Stack Django Engineer',
                'company': 'FutureTech Inc',
                'location': 'Bengaluru, IN',
                'job_type': Job.JOB_TYPE_FULL_TIME,
                'salary': '$95k - $125k',
                'experience': '2-4 years',
                'skills_required': 'Python, Django, Bootstrap 5, SQLite',
                'description': 'Build and scale full-stack CareerConnect web applications.',
                'is_active': 'on',
            },
            follow=True,
        )
        self.assertRedirects(create_response, self.employer_dashboard_url)
        self.assertContains(create_response, 'Job &quot;Full Stack Django Engineer&quot; posted successfully.')

        job = Job.objects.get(title='Full Stack Django Engineer')
        self.assertEqual(job.employer, self.employer)
        self.assertEqual(job.experience, '2-4 years')
        self.assertIsNotNone(job.posted_date)
        self.assertTrue(job.is_active)

        list_response = self.client.get(self.job_list_url)
        self.assertEqual(list_response.status_code, 200)
        self.assertTemplateUsed(list_response, 'jobs/job_list.html')
        self.assertContains(list_response, 'Full Stack Django Engineer')
        self.assertContains(list_response, '2-4 years')

        detail_response = self.client.get(reverse('job_detail', args=[job.id]))
        self.assertEqual(detail_response.status_code, 200)
        self.assertTemplateUsed(detail_response, 'jobs/job_detail.html')
        for detail_text in (
            'Full Stack Django Engineer',
            'FutureTech Inc',
            'Bengaluru, IN',
            '$95k - $125k',
            '2-4 years',
            'Full-Time',
            'Bootstrap 5',
            'Clara Employer',
        ):
            self.assertContains(detail_response, detail_text)

        edit_response = self.client.post(
            reverse('edit_job', args=[job.id]),
            {
                'title': 'Lead Django Engineer',
                'company': 'FutureTech Inc',
                'location': 'Remote',
                'job_type': Job.JOB_TYPE_REMOTE,
                'salary': '$115k - $140k',
                'experience': '4-6 years',
                'skills_required': 'Python, Django, PostgreSQL',
                'description': 'Lead backend development for CareerConnect services.',
                'is_active': '',
            },
            follow=True,
        )
        self.assertRedirects(edit_response, self.employer_dashboard_url)
        self.assertContains(edit_response, 'Job &quot;Lead Django Engineer&quot; updated successfully.')

        job.refresh_from_db()
        self.assertEqual(job.title, 'Lead Django Engineer')
        self.assertEqual(job.experience, '4-6 years')
        self.assertFalse(job.is_active)

        list_after_deactivate = self.client.get(self.job_list_url)
        self.assertNotContains(list_after_deactivate, 'Lead Django Engineer')

        self.client.post(reverse('logout'))
        self.assertEqual(self.client.get(reverse('job_detail', args=[job.id])).status_code, 404)

        self._login('other@example.com')
        self.assertEqual(self.client.get(reverse('edit_job', args=[job.id])).status_code, 403)
        self.assertEqual(self.client.post(reverse('delete_job', args=[job.id])).status_code, 403)
        self.assertTrue(Job.objects.filter(pk=job.id).exists())

        self.client.post(reverse('logout'))
        self._login('emp@example.com')

        delete_response = self.client.post(reverse('delete_job', args=[job.id]), follow=True)
        self.assertRedirects(delete_response, self.employer_dashboard_url)
        self.assertContains(delete_response, 'Job &quot;Lead Django Engineer&quot; deleted successfully.')
        self.assertFalse(Job.objects.filter(pk=job.id).exists())



import tempfile

from django.contrib.auth.models import User
from django.contrib.messages import get_messages
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from accounts.models import UserProfile
from jobs.models import Job, JobApplication


class JobSearchAndApplicationTests(TestCase):
    def setUp(self):
        choices = [choice[0] for choice in Job._meta.get_field('job_type').choices]
        self.type_primary = choices[0]
        self.type_secondary = choices[1] if len(choices) > 1 else choices[0]

        self.employer = User.objects.create_user(
            username='emp_search@example.com',
            email='emp_search@example.com',
            password='Password123!',
        )
        UserProfile.objects.create(
            user=self.employer,
            full_name='Hiring Lead',
            role=UserProfile.ROLE_EMPLOYER,
            company_name='Nimbus Tech',
            company_description='Cloud engineering company',
        )

        self.seeker = User.objects.create_user(
            username='seeker_search@example.com',
            email='seeker_search@example.com',
            password='Password123!',
        )
        self.seeker_profile = UserProfile.objects.create(
            user=self.seeker,
            full_name='Asha Menon',
            role=UserProfile.ROLE_JOB_SEEKER,
            qualification='B.Tech CS',
            skills='Python, Django, SQL',
        )

        self.job_backend = Job.objects.create(
            title='Senior Django Architect',
            company='Nimbus Tech',
            location='Bengaluru',
            job_type=self.type_primary,
            salary='18 LPA',
            experience='4+ years',
            skills_required='Django, PostgreSQL',
            description='Complete backend architecture ownership and API design responsibilities.',
            employer=self.employer,
            is_active=True,
        )
        self.job_frontend = Job.objects.create(
            title='React UI Specialist',
            company='Nimbus Tech',
            location='Hyderabad',
            job_type=self.type_secondary,
            salary='12 LPA',
            experience='2+ years',
            skills_required='React, TypeScript',
            description='Build accessible and responsive web interfaces.',
            employer=self.employer,
            is_active=True,
        )
        self.job_inactive = Job.objects.create(
            title='Archived Legacy Engineer',
            company='Nimbus Tech',
            location='Bengaluru',
            job_type=self.type_primary,
            salary='10 LPA',
            experience='3 years',
            skills_required='Python',
            description='This inactive role should remain hidden.',
            employer=self.employer,
            is_active=False,
        )

    def _login(self, email, password='Password123!'):
        return self.client.post(
            reverse('login'),
            {'email': email, 'password': password},
            follow=True,
        )

    def test_job_list_displays_active_jobs_and_supports_search_and_filters(self):
        all_resp = self.client.get(reverse('job_list'))
        self.assertEqual(all_resp.status_code, 200)
        self.assertTemplateUsed(all_resp, 'jobs/job_list.html')
        self.assertContains(all_resp, 'Senior Django Architect')
        self.assertContains(all_resp, 'React UI Specialist')
        self.assertNotContains(all_resp, 'Archived Legacy Engineer')

        title_resp = self.client.get(reverse('job_list'), {'q': 'Django'})
        self.assertEqual(title_resp.status_code, 200)
        self.assertContains(title_resp, 'Senior Django Architect')
        self.assertNotContains(title_resp, 'React UI Specialist')

        loc_resp = self.client.get(reverse('job_list'), {'location': 'Hyderabad'})
        self.assertEqual(loc_resp.status_code, 200)
        self.assertContains(loc_resp, 'React UI Specialist')
        self.assertNotContains(loc_resp, 'Senior Django Architect')

        type_resp = self.client.get(reverse('job_list'), {'job_type': self.type_secondary})
        self.assertEqual(type_resp.status_code, 200)
        self.assertContains(type_resp, 'React UI Specialist')
        if self.type_secondary != self.type_primary:
            self.assertNotContains(type_resp, 'Senior Django Architect')

        combined_resp = self.client.get(
            reverse('job_list'),
            {
                'q': 'Django',
                'location': 'Bengaluru',
                'job_type': self.type_primary,
            },
        )
        self.assertEqual(combined_resp.status_code, 200)
        self.assertContains(combined_resp, 'Senior Django Architect')
        self.assertNotContains(combined_resp, 'React UI Specialist')

        empty_resp = self.client.get(
            reverse('job_list'),
            {'q': 'Django', 'location': 'Hyderabad'},
        )
        self.assertEqual(empty_resp.status_code, 200)
        self.assertNotContains(empty_resp, 'Senior Django Architect')

    def test_job_detail_shows_full_description_and_apply_form_for_job_seeker(self):
        guest_resp = self.client.get(reverse('job_detail', args=[self.job_backend.id]))
        self.assertEqual(guest_resp.status_code, 200)
        self.assertContains(
            guest_resp,
            'Complete backend architecture ownership and API design responsibilities.',
        )

        self._login('seeker_search@example.com')
        seeker_resp = self.client.get(reverse('job_detail', args=[self.job_backend.id]))
        self.assertEqual(seeker_resp.status_code, 200)
        self.assertIn('application_form', seeker_resp.context)
        self.assertContains(seeker_resp, 'id="apply-section"')
        self.assertContains(seeker_resp, 'enctype="multipart/form-data"')
        self.assertContains(seeker_resp, 'name="resume"')
        self.assertContains(seeker_resp, 'name="cover_note"')

    def test_apply_and_applied_jobs_access_control(self):
        apply_url = reverse('apply_to_job', args=[self.job_backend.id])
        applied_url = reverse('applied_jobs')

        self.assertEqual(self.client.get(apply_url).status_code, 302)
        self.assertEqual(self.client.get(applied_url).status_code, 302)

        self._login('emp_search@example.com')
        self.assertEqual(self.client.get(apply_url).status_code, 403)
        self.assertEqual(self.client.post(apply_url).status_code, 403)
        self.assertEqual(self.client.get(applied_url).status_code, 403)

    def test_complete_application_with_resume_upload_duplicate_prevention_and_applied_jobs(self):
        apply_url = reverse('apply_to_job', args=[self.job_backend.id])
        applied_url = reverse('applied_jobs')

        self._login('seeker_search@example.com')

        get_apply = self.client.get(f'{apply_url}?next={applied_url}')
        self.assertEqual(get_apply.status_code, 200)
        self.assertTemplateUsed(get_apply, 'jobs/apply_job.html')
        self.assertContains(get_apply, 'Senior Django Architect')

        with tempfile.TemporaryDirectory() as media_dir:
            with override_settings(MEDIA_ROOT=media_dir):
                invalid_txt = SimpleUploadedFile(
                    'resume.txt',
                    b'Plain text resume',
                    content_type='text/plain',
                )
                bad_resp = self.client.post(
                    apply_url,
                    {
                        'resume': invalid_txt,
                        'cover_note': 'Should be rejected.',
                        'next': applied_url,
                    },
                )
                self.assertEqual(bad_resp.status_code, 200)
                self.assertEqual(JobApplication.objects.count(), 0)

                fake_pdf = SimpleUploadedFile(
                    'fake.pdf',
                    b'NOT_A_PDF_HEADER',
                    content_type='application/pdf',
                )
                bad_magic_resp = self.client.post(
                    apply_url,
                    {
                        'resume': fake_pdf,
                        'cover_note': 'Invalid header.',
                        'next': applied_url,
                    },
                )
                self.assertEqual(bad_magic_resp.status_code, 200)
                self.assertEqual(JobApplication.objects.count(), 0)

                valid_pdf = SimpleUploadedFile(
                    'asha_cv.pdf',
                    b'%PDF-1.4\n%Asha Menon Resume\n%%EOF',
                    content_type='application/pdf',
                )
                success_resp = self.client.post(
                    apply_url,
                    {
                        'resume': valid_pdf,
                        'cover_note': 'Built scalable Django services for 4 years.',
                        'next': applied_url,
                    },
                    follow=True,
                )
                self.assertRedirects(success_resp, applied_url)
                self.assertTemplateUsed(success_resp, 'jobs/applied_jobs.html')
                self.assertContains(success_resp, 'Senior Django Architect')
                self.assertContains(success_resp, 'Built scalable Django services for 4 years.')
                self.assertContains(success_resp, 'asha_cv')

                application = JobApplication.objects.get(
                    job=self.job_backend,
                    applicant=self.seeker,
                )
                self.assertEqual(
                    application.cover_note,
                    'Built scalable Django services for 4 years.',
                )
                self.assertTrue(bool(application.resume.name))
                self.assertEqual(application.effective_resume.name, application.resume.name)
                self.assertIn('asha_cv', application.resume_filename)

                dup_post = self.client.post(
                    apply_url,
                    {
                        'cover_note': 'Second attempt.',
                        'next': applied_url,
                    },
                    follow=True,
                )
                self.assertEqual(
                    JobApplication.objects.filter(
                        job=self.job_backend,
                        applicant=self.seeker,
                    ).count(),
                    1,
                )
                dup_msgs = [str(m) for m in get_messages(dup_post.wsgi_request)]
                self.assertTrue(dup_msgs)

                dup_get = self.client.get(f'{apply_url}?next={applied_url}', follow=True)
                self.assertRedirects(dup_get, applied_url)

                self.client.post(reverse('logout'))
                self._login('emp_search@example.com')
                emp_resp = self.client.get(reverse('employer_dashboard'))
                self.assertEqual(emp_resp.status_code, 200)
                self.assertContains(emp_resp, 'Asha Menon')
                self.assertContains(emp_resp, 'Built scalable Django services for 4 years.')
                self.assertContains(emp_resp, 'View Resume')
                self.assertContains(emp_resp, application.effective_resume.url)



from .models import ApplicationStatusHistory


class ApplicationManagementTests(TestCase):
    """Verify employer/job-seeker application management, resume downloads, statuses, and history."""

    def setUp(self):
        self.login_url = reverse('login')
        self.employer_dashboard_url = reverse('employer_dashboard')
        self.seeker_dashboard_url = reverse('job_seeker_dashboard')
        self.applied_jobs_url = reverse('applied_jobs')
        self.password = 'ManagePass#2026'

        self.employer_a = User.objects.create_user(
            username='emp_mgr_a@example.com',
            email='emp_mgr_a@example.com',
            password=self.password,
        )
        UserProfile.objects.create(
            user=self.employer_a,
            full_name='Meera Hiring',
            role=UserProfile.ROLE_EMPLOYER,
            company_name='Orbit Systems',
        )

        self.employer_b = User.objects.create_user(
            username='emp_mgr_b@example.com',
            email='emp_mgr_b@example.com',
            password=self.password,
        )
        UserProfile.objects.create(
            user=self.employer_b,
            full_name='Vikram Other',
            role=UserProfile.ROLE_EMPLOYER,
            company_name='Zenith Corp',
        )

        self.seeker_a = User.objects.create_user(
            username='rohan@example.com',
            email='rohan@example.com',
            password=self.password,
        )
        self.profile_a = UserProfile.objects.create(
            user=self.seeker_a,
            full_name='Rohan Kulkarni',
            role=UserProfile.ROLE_JOB_SEEKER,
            qualification='B.E. Computer Engineering',
            skills='Python, Django, REST APIs',
        )

        self.seeker_b = User.objects.create_user(
            username='priya@example.com',
            email='priya@example.com',
            password=self.password,
        )
        self.profile_b = UserProfile.objects.create(
            user=self.seeker_b,
            full_name='Priya Nair',
            role=UserProfile.ROLE_JOB_SEEKER,
            qualification='MCA',
            skills='Python, SQL',
        )

        self.job_a = Job.objects.create(
            title='Backend Platform Developer',
            company='Orbit Systems',
            location='Pune, IN',
            job_type=Job.JOB_TYPE_FULL_TIME,
            salary='16 LPA',
            experience='3+ years',
            skills_required='Python, Django',
            description='Build backend APIs and data workflows for Orbit Systems.',
            employer=self.employer_a,
            is_active=True,
        )
        self.job_b = Job.objects.create(
            title='Zenith Secret Role',
            company='Zenith Corp',
            location='Remote',
            job_type=Job.JOB_TYPE_REMOTE,
            salary='20 LPA',
            experience='4+ years',
            skills_required='Go, Kubernetes',
            description='Private job posting belonging to Zenith Corp.',
            employer=self.employer_b,
            is_active=True,
        )

    def _login(self, email):
        return self.client.post(
            self.login_url,
            {'email': email, 'password': self.password},
            follow=True,
        )

    def test_application_status_choices_and_initial_history(self):
        self.assertEqual(
            JobApplication.STATUS_CHOICES,
            [
                ('applied', 'Applied'),
                ('shortlisted', 'Shortlisted'),
                ('rejected', 'Rejected'),
                ('selected', 'Selected'),
            ],
        )

        app = JobApplication.objects.create(job=self.job_a, applicant=self.seeker_a)
        self.assertEqual(app.status, JobApplication.STATUS_APPLIED)
        self.assertEqual(app.get_status_display(), 'Applied')
        history = list(app.status_history.values_list('status', flat=True))
        self.assertEqual(history, [JobApplication.STATUS_APPLIED])

    def test_employer_views_own_applicants_and_downloads_resumes_securely(self):
        pdf_bytes = b'%PDF-1.4\n%Rohan Kulkarni Resume PDF\n%%EOF'
        profile_pdf_bytes = b'%PDF-1.4\n%Priya Nair Profile Resume PDF\n%%EOF'

        with tempfile.TemporaryDirectory() as media_dir:
            with override_settings(MEDIA_ROOT=media_dir):
                app_with_upload = JobApplication.objects.create(
                    job=self.job_a,
                    applicant=self.seeker_a,
                    resume=SimpleUploadedFile(
                        'rohan_cv.pdf',
                        pdf_bytes,
                        content_type='application/pdf',
                    ),
                    cover_note='Excited about Orbit Systems.',
                )
                self.profile_b.resume = SimpleUploadedFile(
                    'priya_profile.pdf',
                    profile_pdf_bytes,
                    content_type='application/pdf',
                )
                self.profile_b.save()
                app_with_profile_resume = JobApplication.objects.create(
                    job=self.job_a,
                    applicant=self.seeker_b,
                )
                other_employer_app = JobApplication.objects.create(
                    job=self.job_b,
                    applicant=self.seeker_a,
                )

                download_url = reverse('download_applicant_resume', args=[app_with_upload.id])
                fallback_download_url = reverse(
                    'download_applicant_resume',
                    args=[app_with_profile_resume.id],
                )
                missing_resume_url = reverse(
                    'download_applicant_resume',
                    args=[other_employer_app.id],
                )

                self.assertEqual(self.client.get(download_url).status_code, 302)

                self._login('emp_mgr_a@example.com')
                dash_resp = self.client.get(self.employer_dashboard_url)
                self.assertEqual(dash_resp.status_code, 200)
                self.assertContains(dash_resp, 'Rohan Kulkarni')
                self.assertContains(dash_resp, 'rohan@example.com')
                self.assertContains(dash_resp, 'Priya Nair')
                self.assertContains(dash_resp, 'priya@example.com')
                self.assertContains(dash_resp, 'Download Resume')
                self.assertContains(dash_resp, download_url)
                self.assertNotContains(dash_resp, 'Zenith Secret Role')

                download_resp = self.client.get(download_url)
                self.assertEqual(download_resp.status_code, 200)
                self.assertEqual(download_resp['Content-Type'], 'application/pdf')
                self.assertIn('attachment;', download_resp['Content-Disposition'])
                self.assertIn('rohan_cv', download_resp['Content-Disposition'])
                self.assertEqual(b''.join(download_resp.streaming_content), pdf_bytes)
                download_resp.close()

                fallback_resp = self.client.get(fallback_download_url)
                self.assertEqual(fallback_resp.status_code, 200)
                self.assertIn('priya_profile', fallback_resp['Content-Disposition'])
                self.assertEqual(b''.join(fallback_resp.streaming_content), profile_pdf_bytes)
                fallback_resp.close()

                self.assertEqual(self.client.get(missing_resume_url).status_code, 403)

                self.client.post(reverse('logout'))
                self._login('priya@example.com')
                self.assertEqual(self.client.get(download_url).status_code, 403)
                own_download = self.client.get(fallback_download_url)
                self.assertEqual(own_download.status_code, 200)
                own_download.close()

                self.client.post(reverse('logout'))
                self._login('emp_mgr_b@example.com')
                self.assertEqual(self.client.get(download_url).status_code, 403)
                self.assertEqual(self.client.get(missing_resume_url).status_code, 404)

    def test_all_application_status_workflows_and_dashboard_history(self):
        app_rohan = JobApplication.objects.create(job=self.job_a, applicant=self.seeker_a)
        app_priya = JobApplication.objects.create(job=self.job_a, applicant=self.seeker_b)
        status_url_rohan = reverse('update_application_status', args=[app_rohan.id])
        status_url_priya = reverse('update_application_status', args=[app_priya.id])

        self._login('emp_mgr_a@example.com')

        step1 = self.client.post(
            status_url_rohan,
            {'status': JobApplication.STATUS_SHORTLISTED, 'next': self.employer_dashboard_url},
            follow=True,
        )
        self.assertRedirects(step1, self.employer_dashboard_url)
        self.assertContains(step1, 'updated to Shortlisted.')

        step2 = self.client.post(
            status_url_rohan,
            {'status': JobApplication.STATUS_SELECTED, 'next': self.employer_dashboard_url},
            follow=True,
        )
        self.assertRedirects(step2, self.employer_dashboard_url)
        self.assertContains(step2, 'updated to Selected.')

        self.client.post(
            status_url_priya,
            {'status': JobApplication.STATUS_SHORTLISTED, 'next': self.employer_dashboard_url},
        )
        reject_resp = self.client.post(
            status_url_priya,
            {'status': JobApplication.STATUS_REJECTED, 'next': self.employer_dashboard_url},
            follow=True,
        )
        self.assertRedirects(reject_resp, self.employer_dashboard_url)
        self.assertContains(reject_resp, 'updated to Rejected.')

        noop_resp = self.client.post(
            status_url_priya,
            {'status': JobApplication.STATUS_REJECTED, 'next': self.employer_dashboard_url},
            follow=True,
        )
        self.assertContains(noop_resp, 'is already Rejected.')

        invalid_resp = self.client.post(
            status_url_priya,
            {'status': 'invalid_state', 'next': self.employer_dashboard_url},
            follow=True,
        )
        self.assertContains(invalid_resp, 'Please select a valid application status.')

        app_rohan.refresh_from_db()
        app_priya.refresh_from_db()
        self.assertEqual(app_rohan.status, JobApplication.STATUS_SELECTED)
        self.assertEqual(app_priya.status, JobApplication.STATUS_REJECTED)

        self.assertEqual(
            list(app_rohan.status_history.values_list('status', flat=True)),
            [
                JobApplication.STATUS_APPLIED,
                JobApplication.STATUS_SHORTLISTED,
                JobApplication.STATUS_SELECTED,
            ],
        )
        self.assertEqual(
            list(app_priya.status_history.values_list('status', flat=True)),
            [
                JobApplication.STATUS_APPLIED,
                JobApplication.STATUS_SHORTLISTED,
                JobApplication.STATUS_REJECTED,
            ],
        )

        emp_dash = self.client.get(self.employer_dashboard_url)
        self.assertContains(emp_dash, 'Applied (0)')
        self.assertContains(emp_dash, 'Shortlisted (0)')
        self.assertContains(emp_dash, 'Rejected (1)')
        self.assertContains(emp_dash, 'Selected (1)')

        selected_only = self.client.get(self.employer_dashboard_url, {'status': 'selected'})
        self.assertEqual(selected_only.status_code, 200)
        self.assertContains(selected_only, 'Rohan Kulkarni')
        self.assertNotContains(selected_only, 'Priya Nair')

        bad_filter = self.client.get(
            self.employer_dashboard_url,
            {'status': 'unknown'},
            follow=True,
        )
        self.assertRedirects(bad_filter, self.employer_dashboard_url)
        self.assertContains(bad_filter, 'Invalid application status filter specified.')

        self.client.post(reverse('logout'))
        self._login('rohan@example.com')

        rohan_dash = self.client.get(self.seeker_dashboard_url)
        self.assertEqual(rohan_dash.status_code, 200)
        self.assertContains(rohan_dash, 'Applied Jobs &amp; Application History')
        self.assertContains(rohan_dash, 'Backend Platform Developer')
        self.assertContains(rohan_dash, 'Selected')
        self.assertContains(rohan_dash, 'Shortlisted')
        self.assertContains(rohan_dash, 'History:')

        rohan_selected = self.client.get(self.seeker_dashboard_url, {'status': 'selected'})
        self.assertEqual(list(rohan_selected.context['applications']), [app_rohan])
        self.assertContains(rohan_selected, 'Backend Platform Developer')
        rohan_rejected = self.client.get(self.seeker_dashboard_url, {'status': 'rejected'})
        self.assertEqual(list(rohan_rejected.context['applications']), [])
        self.assertContains(rohan_rejected, 'No applications with status "Rejected" yet.')

        rohan_applied_page = self.client.get(self.applied_jobs_url)
        self.assertContains(rohan_applied_page, 'Selected')
        self.assertContains(rohan_applied_page, 'History:')
        rohan_applied_filtered = self.client.get(self.applied_jobs_url, {'status': 'rejected'})
        self.assertNotContains(rohan_applied_filtered, 'Backend Platform Developer')

        rohan_detail = self.client.get(reverse('job_detail', args=[self.job_a.id]))
        self.assertContains(rohan_detail, 'Already Applied')
        self.assertContains(rohan_detail, 'Selected')

        self.client.post(reverse('logout'))
        self._login('priya@example.com')
        priya_dash = self.client.get(self.seeker_dashboard_url)
        self.assertContains(priya_dash, 'Rejected')
        self.assertContains(priya_dash, 'Shortlisted')

    def test_update_application_status_access_control(self):
        app = JobApplication.objects.create(job=self.job_a, applicant=self.seeker_a)
        status_url = reverse('update_application_status', args=[app.id])

        self.assertRedirects(
            self.client.post(status_url, {'status': JobApplication.STATUS_SHORTLISTED}),
            f'{self.login_url}?next={status_url}',
        )

        self._login('rohan@example.com')
        self.assertEqual(
            self.client.post(status_url, {'status': JobApplication.STATUS_SELECTED}).status_code,
            403,
        )

        self.client.post(reverse('logout'))
        self._login('emp_mgr_b@example.com')
        self.assertEqual(
            self.client.post(status_url, {'status': JobApplication.STATUS_REJECTED}).status_code,
            403,
        )

        self.client.post(reverse('logout'))
        self._login('emp_mgr_a@example.com')
        self.assertEqual(self.client.get(status_url).status_code, 405)

        app.refresh_from_db()
        self.assertEqual(app.status, JobApplication.STATUS_APPLIED)
        self.assertEqual(ApplicationStatusHistory.objects.filter(application=app).count(), 1)



import re


class EndToEndPortalVerificationTests(TestCase):
    """Verify full cross-app portal workflows, inactive applied links, and rendered navigation links."""

    def _assert_no_broken_internal_links(self, response):
        html = response.content.decode('utf-8')
        self.assertNotIn('href="#"', html)
        self.assertNotIn('href=""', html)
        self.assertNotIn('action=""', html)

        hrefs = set(re.findall(r'href="(/[^"]*)"', html))
        for href in hrefs:
            path = href.split('#', 1)[0]
            if not path or path.startswith('/static/') or path.startswith('/media/'):
                continue
            link_resp = self.client.get(path)
            self.assertIn(
                link_resp.status_code,
                (200, 302),
                f'Broken internal link {href} returned {link_resp.status_code}',
            )
            if hasattr(link_resp, 'close'):
                link_resp.close()

    def test_applied_job_remains_viewable_when_deactivated(self):
        employer = User.objects.create_user(
            username='emp_close@example.com',
            email='emp_close@example.com',
            password='Password#2026',
        )
        UserProfile.objects.create(
            user=employer,
            full_name='Closing Employer',
            role=UserProfile.ROLE_EMPLOYER,
            company_name='CloseTest Co',
        )
        applicant = User.objects.create_user(
            username='seeker_close@example.com',
            email='seeker_close@example.com',
            password='Password#2026',
        )
        UserProfile.objects.create(
            user=applicant,
            full_name='Applicant User',
            role=UserProfile.ROLE_JOB_SEEKER,
        )
        other_seeker = User.objects.create_user(
            username='other_seeker@example.com',
            email='other_seeker@example.com',
            password='Password#2026',
        )
        UserProfile.objects.create(
            user=other_seeker,
            full_name='Other Seeker',
            role=UserProfile.ROLE_JOB_SEEKER,
        )
        job = Job.objects.create(
            title='Closing Soon Engineer',
            company='CloseTest Co',
            location='Remote',
            job_type=Job.JOB_TYPE_REMOTE,
            salary='15 LPA',
            experience='2 years',
            skills_required='Python, Django',
            description='Role that closes after applications are received.',
            employer=employer,
            is_active=True,
        )
        JobApplication.objects.create(job=job, applicant=applicant)

        job.is_active = False
        job.save(update_fields=['is_active'])

        detail_url = reverse('job_detail', args=[job.id])
        self.assertEqual(self.client.get(detail_url).status_code, 404)

        self.client.post(
            reverse('login'),
            {'email': 'other_seeker@example.com', 'password': 'Password#2026'},
        )
        self.assertEqual(self.client.get(detail_url).status_code, 404)

        self.client.post(reverse('logout'))
        self.client.post(
            reverse('login'),
            {'email': 'seeker_close@example.com', 'password': 'Password#2026'},
        )
        applicant_detail = self.client.get(detail_url)
        self.assertEqual(applicant_detail.status_code, 200)
        self.assertContains(applicant_detail, 'Closing Soon Engineer')
        self.assertContains(applicant_detail, 'Inactive')
        self.assertContains(applicant_detail, 'Already Applied')

    def test_superuser_without_profile_and_full_portal_workflow_with_link_checks(self):
        plain_user = User.objects.create_user(
            username='plain_no_profile',
            email='plain@example.com',
            password='PlainPass#2026',
        )
        self.client.force_login(plain_user)
        plain_dash = self.client.get(reverse('dashboard'), follow=True)
        self.assertRedirects(plain_dash, reverse('home'))
        self.assertContains(plain_dash, 'No portal profile is assigned to this account.')
        self._assert_no_broken_internal_links(plain_dash)
        self.client.post(reverse('logout'))

        superuser = User.objects.create_superuser(
            username='admin_user',
            email='admin@example.com',
            password='AdminPass#2026',
        )
        self.client.force_login(superuser)
        dash_redir = self.client.get(reverse('dashboard'), follow=True)
        self.assertRedirects(dash_redir, reverse('admin_dashboard'))
        self.assertContains(dash_redir, 'Platform Administration')
        self._assert_no_broken_internal_links(dash_redir)
        self.client.post(reverse('logout'))

        self._assert_no_broken_internal_links(self.client.get(reverse('home')))
        self._assert_no_broken_internal_links(self.client.get(reverse('job_list')))
        self._assert_no_broken_internal_links(self.client.get(reverse('login')))
        self._assert_no_broken_internal_links(self.client.get(reverse('register')))

        emp_reg = self.client.post(
            reverse('register'),
            {
                'full_name': 'Neha Kapoor',
                'email': 'neha.e2e@example.com',
                'role': UserProfile.ROLE_EMPLOYER,
                'password': 'StrongPass#2026',
                'confirm_password': 'StrongPass#2026',
            },
            follow=True,
        )
        self.assertRedirects(emp_reg, reverse('login'))

        emp_login = self.client.post(
            reverse('login'),
            {'email': 'neha.e2e@example.com', 'password': 'StrongPass#2026'},
            follow=True,
        )
        self.assertRedirects(emp_login, reverse('employer_dashboard'))

        self.client.post(
            reverse('employer_dashboard'),
            {
                'full_name': 'Neha Kapoor',
                'company_name': 'Vertex Cloud',
                'company_description': 'Distributed backend infrastructure.',
                'location': 'Bengaluru',
                'phone': '+91 98888 77777',
            },
            follow=True,
        )
        self.client.post(
            reverse('create_job'),
            {
                'title': 'E2E Django Engineer',
                'company': 'Vertex Cloud',
                'location': 'Bengaluru',
                'job_type': Job.JOB_TYPE_HYBRID,
                'salary': '18 LPA',
                'experience': '3 years',
                'skills_required': 'Python, Django, SQLite',
                'description': 'Full lifecycle backend development on CareerConnect.',
                'is_active': 'on',
            },
            follow=True,
        )
        e2e_job = Job.objects.get(title='E2E Django Engineer')
        emp_dash = self.client.get(reverse('employer_dashboard'))
        self._assert_no_broken_internal_links(emp_dash)
        self.client.post(reverse('logout'))

        seeker_reg = self.client.post(
            reverse('register'),
            {
                'full_name': 'Kabir Verma',
                'email': 'kabir.e2e@example.com',
                'role': UserProfile.ROLE_JOB_SEEKER,
                'password': 'StrongPass#2026',
                'confirm_password': 'StrongPass#2026',
            },
            follow=True,
        )
        self.assertRedirects(seeker_reg, reverse('login'))

        seeker_login = self.client.post(
            reverse('login'),
            {'email': 'kabir.e2e@example.com', 'password': 'StrongPass#2026'},
            follow=True,
        )
        self.assertRedirects(seeker_login, reverse('job_seeker_dashboard'))

        search_resp = self.client.get(
            reverse('job_list'),
            {'q': 'E2E Django', 'location': 'Bengaluru', 'job_type': Job.JOB_TYPE_HYBRID},
        )
        self.assertContains(search_resp, 'E2E Django Engineer')
        self._assert_no_broken_internal_links(search_resp)
        self._assert_no_broken_internal_links(self.client.get(reverse('job_detail', args=[e2e_job.id])))

        with tempfile.TemporaryDirectory() as media_dir:
            with override_settings(MEDIA_ROOT=media_dir):
                pdf_payload = b'%PDF-1.4\n%Kabir Verma CV\n%%EOF'
                self.client.post(
                    reverse('apply_to_job', args=[e2e_job.id]),
                    {
                        'resume': SimpleUploadedFile(
                            'kabir_e2e.pdf',
                            pdf_payload,
                            content_type='application/pdf',
                        ),
                        'cover_note': 'Passionate Django engineer.',
                        'next': reverse('applied_jobs'),
                    },
                    follow=True,
                )
                application = JobApplication.objects.get(job=e2e_job)

                self._assert_no_broken_internal_links(self.client.get(reverse('job_seeker_dashboard')))
                self._assert_no_broken_internal_links(self.client.get(reverse('applied_jobs')))
                self._assert_no_broken_internal_links(self.client.get(reverse('job_detail', args=[e2e_job.id])))

                self.client.post(reverse('logout'))
                self.client.post(
                    reverse('login'),
                    {'email': 'neha.e2e@example.com', 'password': 'StrongPass#2026'},
                )
                self._assert_no_broken_internal_links(self.client.get(reverse('employer_dashboard')))

                resume_resp = self.client.get(reverse('download_applicant_resume', args=[application.id]))
                self.assertEqual(resume_resp.status_code, 200)
                self.assertEqual(b''.join(resume_resp.streaming_content), pdf_payload)
                resume_resp.close()

                for target_status in (
                    JobApplication.STATUS_SHORTLISTED,
                    JobApplication.STATUS_SELECTED,
                ):
                    self.client.post(
                        reverse('update_application_status', args=[application.id]),
                        {'status': target_status, 'next': reverse('employer_dashboard')},
                        follow=True,
                    )

                self.client.post(reverse('logout'))
                self.client.post(
                    reverse('login'),
                    {'email': 'kabir.e2e@example.com', 'password': 'StrongPass#2026'},
                )
                final_applied = self.client.get(reverse('applied_jobs'))
                self.assertContains(final_applied, 'Selected')
                self.assertContains(final_applied, 'Shortlisted')
                self.assertContains(final_applied, 'Applied')
                logout_resp = self.client.post(reverse('logout'), follow=True)
                self.assertRedirects(logout_resp, reverse('login'))
                self.assertRedirects(
                    self.client.get(reverse('job_seeker_dashboard')),
                    f"{reverse('login')}?next={reverse('job_seeker_dashboard')}",
                )



from django.contrib import admin as django_admin

from .admin import JobApplicationAdmin


class AdminApplicationManagementTests(TestCase):
    """Verify Django Admin view, search, filter, resume preview, and status updates for applications."""

    def setUp(self):
        self.password = 'AdminTest#2026'
        self.admin_user = User.objects.create_superuser(
            username='portal_admin',
            email='portal_admin@example.com',
            password=self.password,
        )

        self.employer_1 = User.objects.create_user(
            username='adm_emp1@example.com',
            email='adm_emp1@example.com',
            password=self.password,
        )
        UserProfile.objects.create(
            user=self.employer_1,
            full_name='Deepa Employer',
            role=UserProfile.ROLE_EMPLOYER,
            company_name='AlphaWorks',
        )
        self.employer_2 = User.objects.create_user(
            username='adm_emp2@example.com',
            email='adm_emp2@example.com',
            password=self.password,
        )
        UserProfile.objects.create(
            user=self.employer_2,
            full_name='Sanjay Hiring',
            role=UserProfile.ROLE_EMPLOYER,
            company_name='BetaGrid',
        )

        self.seeker_1 = User.objects.create_user(
            username='ananya.rao@example.com',
            email='ananya.rao@example.com',
            password=self.password,
        )
        UserProfile.objects.create(
            user=self.seeker_1,
            full_name='Ananya Rao',
            role=UserProfile.ROLE_JOB_SEEKER,
        )
        self.seeker_2 = User.objects.create_user(
            username='ramesh.k@example.com',
            email='ramesh.k@example.com',
            password=self.password,
        )
        UserProfile.objects.create(
            user=self.seeker_2,
            full_name='Ramesh Kulkarni',
            role=UserProfile.ROLE_JOB_SEEKER,
        )

        self.job_1 = Job.objects.create(
            title='Platform Architect',
            company='AlphaWorks',
            location='Bengaluru',
            job_type=Job.JOB_TYPE_FULL_TIME,
            salary='24 LPA',
            experience='5+ years',
            skills_required='Python, Django',
            description='Lead backend architecture for AlphaWorks platform.',
            employer=self.employer_1,
            is_active=True,
        )
        self.job_2 = Job.objects.create(
            title='Cloud QA Lead',
            company='BetaGrid',
            location='Remote',
            job_type=Job.JOB_TYPE_REMOTE,
            salary='18 LPA',
            experience='4+ years',
            skills_required='Pytest, Selenium',
            description='Own automated release verification across BetaGrid.',
            employer=self.employer_2,
            is_active=True,
        )

        self.changelist_url = reverse('admin:jobs_jobapplication_changelist')
        self.add_url = reverse('admin:jobs_jobapplication_add')

    def test_job_application_registered_in_admin_and_protected(self):
        self.assertIn(JobApplication, django_admin.site._registry)
        self.assertIsInstance(django_admin.site._registry[JobApplication], JobApplicationAdmin)

        self.assertEqual(self.client.get(self.changelist_url).status_code, 302)
        self.client.force_login(self.seeker_1)
        self.assertEqual(self.client.get(self.changelist_url).status_code, 302)
        self.client.force_login(self.employer_1)
        self.assertEqual(self.client.get(self.changelist_url).status_code, 302)

    def test_admin_can_view_search_filter_and_open_resumes(self):
        pdf_bytes = b'%PDF-1.4\n%Ananya Rao Resume\n%%EOF'

        with tempfile.TemporaryDirectory() as media_dir:
            with override_settings(MEDIA_ROOT=media_dir):
                app_1 = JobApplication.objects.create(
                    job=self.job_1,
                    applicant=self.seeker_1,
                    status=JobApplication.STATUS_APPLIED,
                    resume=SimpleUploadedFile(
                        'ananya_resume.pdf',
                        pdf_bytes,
                        content_type='application/pdf',
                    ),
                )
                app_2 = JobApplication.objects.create(
                    job=self.job_2,
                    applicant=self.seeker_2,
                    status=JobApplication.STATUS_SHORTLISTED,
                )

                self.client.force_login(self.admin_user)

                add_resp = self.client.get(self.add_url)
                self.assertEqual(add_resp.status_code, 200)

                list_resp = self.client.get(self.changelist_url)
                self.assertEqual(list_resp.status_code, 200)
                for expected in (
                    'Ananya Rao',
                    'ananya.rao@example.com',
                    'Platform Architect',
                    'Ramesh Kulkarni',
                    'ramesh.k@example.com',
                    'Cloud QA Lead',
                    'Application Date',
                    'View Resume',
                    'No resume uploaded',
                ):
                    self.assertContains(list_resp, expected)

                by_name = self.client.get(self.changelist_url, {'q': 'Ananya'})
                self.assertContains(by_name, 'Ananya Rao')
                self.assertNotContains(by_name, 'Ramesh Kulkarni')

                by_title = self.client.get(self.changelist_url, {'q': 'Cloud QA Lead'})
                self.assertContains(by_title, 'Ramesh Kulkarni')
                self.assertNotContains(by_title, 'Ananya Rao')

                by_status = self.client.get(
                    self.changelist_url,
                    {'status__exact': JobApplication.STATUS_SHORTLISTED},
                )
                self.assertContains(by_status, 'Ramesh Kulkarni')
                self.assertNotContains(by_status, 'Ananya Rao')

                today_year = str(app_1.applied_at.year)
                by_date = self.client.get(self.changelist_url, {'applied_at__year': today_year})
                self.assertEqual(by_date.status_code, 200)
                self.assertContains(by_date, 'Ananya Rao')

                change_url = reverse('admin:jobs_jobapplication_change', args=[app_1.id])
                change_resp = self.client.get(change_url)
                self.assertEqual(change_resp.status_code, 200)
                self.assertContains(change_resp, 'Ananya Rao')
                self.assertContains(change_resp, 'ananya.rao@example.com')
                self.assertContains(change_resp, 'View Resume')

                inline_url = f"{reverse('download_applicant_resume', args=[app_1.id])}?inline=1"
                inline_resp = self.client.get(inline_url)
                self.assertEqual(inline_resp.status_code, 200)
                self.assertEqual(inline_resp['Content-Type'], 'application/pdf')
                self.assertIn('inline;', inline_resp['Content-Disposition'])
                self.assertEqual(b''.join(inline_resp.streaming_content), pdf_bytes)
                inline_resp.close()

                dl_resp = self.client.get(reverse('download_applicant_resume', args=[app_1.id]))
                self.assertEqual(dl_resp.status_code, 200)
                self.assertIn('attachment;', dl_resp['Content-Disposition'])
                dl_resp.close()

                app_2_url = reverse('download_applicant_resume', args=[app_2.id])
                self.assertEqual(self.client.get(app_2_url).status_code, 404)

    def test_admin_can_update_application_status_and_records_history(self):
        app_1 = JobApplication.objects.create(job=self.job_1, applicant=self.seeker_1)
        app_2 = JobApplication.objects.create(job=self.job_2, applicant=self.seeker_2)
        change_url = reverse('admin:jobs_jobapplication_change', args=[app_1.id])

        self.client.force_login(self.admin_user)

        initial_history = app_1.status_history.first()
        history_count = app_1.status_history.count()
        change_post = self.client.post(
            change_url,
            {
                'job': str(self.job_1.id),
                'applicant': str(self.seeker_1.id),
                'status': JobApplication.STATUS_SHORTLISTED,
                'cover_note': 'Reviewed by portal admin.',
                'status_history-TOTAL_FORMS': str(history_count),
                'status_history-INITIAL_FORMS': str(history_count),
                'status_history-MIN_NUM_FORMS': '0',
                'status_history-MAX_NUM_FORMS': '1000',
                'status_history-0-id': str(initial_history.id),
                'status_history-0-application': str(app_1.id),
            },
            follow=True,
        )
        self.assertRedirects(change_post, self.changelist_url)
        app_1.refresh_from_db()
        self.assertEqual(app_1.status, JobApplication.STATUS_SHORTLISTED)
        self.assertEqual(
            list(app_1.status_history.values_list('status', flat=True)),
            [JobApplication.STATUS_APPLIED, JobApplication.STATUS_SHORTLISTED],
        )
        self.assertEqual(app_1.status_history.last().changed_by, self.admin_user)

        bulk_post = self.client.post(
            self.changelist_url,
            {
                'action': 'mark_as_selected',
                'select_across': '0',
                'index': '0',
                '_selected_action': [str(app_1.id), str(app_2.id)],
            },
            follow=True,
        )
        self.assertEqual(bulk_post.status_code, 200)
        self.assertContains(bulk_post, 'Updated 2 application(s) to Selected.')
        app_1.refresh_from_db()
        app_2.refresh_from_db()
        self.assertEqual(app_1.status, JobApplication.STATUS_SELECTED)
        self.assertEqual(app_2.status, JobApplication.STATUS_SELECTED)

        inline_save = self.client.post(
            self.changelist_url,
            {
                'action': '',
                'index': '0',
                'form-TOTAL_FORMS': '2',
                'form-INITIAL_FORMS': '2',
                'form-MIN_NUM_FORMS': '0',
                'form-MAX_NUM_FORMS': '1000',
                'form-0-id': str(app_2.id),
                'form-0-status': JobApplication.STATUS_REJECTED,
                'form-1-id': str(app_1.id),
                'form-1-status': JobApplication.STATUS_SELECTED,
                '_save': 'Save',
            },
            follow=True,
        )
        self.assertEqual(inline_save.status_code, 200)
        app_2.refresh_from_db()
        self.assertEqual(app_2.status, JobApplication.STATUS_REJECTED)
        self.assertEqual(
            list(app_2.status_history.values_list('status', flat=True)),
            [
                JobApplication.STATUS_APPLIED,
                JobApplication.STATUS_SELECTED,
                JobApplication.STATUS_REJECTED,
            ],
        )


class AdminPortalDashboardTests(TestCase):
    """Verify the CareerConnect Admin Dashboard metrics and in-portal application management."""

    def setUp(self):
        self.admin_dashboard_url = reverse('admin_dashboard')
        self.login_url = reverse('login')

        self.admin_user = User.objects.create_superuser(
            username='portal_admin',
            email='portaladmin@example.com',
            password='Password#2026',
        )
        self.employer_1 = User.objects.create_user(
            username='emp_one@example.com',
            email='emp_one@example.com',
            password='Password#2026',
        )
        UserProfile.objects.create(
            user=self.employer_1,
            full_name='Meera Verma',
            role=UserProfile.ROLE_EMPLOYER,
            company_name='CloudScale Systems',
        )
        self.employer_2 = User.objects.create_user(
            username='emp_two@example.com',
            email='emp_two@example.com',
            password='Password#2026',
        )
        UserProfile.objects.create(
            user=self.employer_2,
            full_name='Vikram Rao',
            role=UserProfile.ROLE_EMPLOYER,
            company_name='DataForge Labs',
        )
        self.seeker_1 = User.objects.create_user(
            username='ananya@example.com',
            email='ananya@example.com',
            password='Password#2026',
        )
        UserProfile.objects.create(
            user=self.seeker_1,
            full_name='Ananya Deshmukh',
            role=UserProfile.ROLE_JOB_SEEKER,
            qualification='B.Tech Computer Science',
            skills='Python, Django, SQL',
        )
        self.seeker_2 = User.objects.create_user(
            username='karan@example.com',
            email='karan@example.com',
            password='Password#2026',
        )
        UserProfile.objects.create(
            user=self.seeker_2,
            full_name='Karan Malhotra',
            role=UserProfile.ROLE_JOB_SEEKER,
            qualification='M.Sc Data Science',
            skills='Pandas, PyTorch',
        )

        self.job_1 = Job.objects.create(
            employer=self.employer_1,
            title='Senior Python Engineer',
            company='CloudScale Systems',
            description='Build resilient backend microservices.',
            location='Bengaluru',
            salary='18-24 LPA',
            job_type=Job.JOB_TYPE_FULL_TIME,
            skills_required='Python, Django',
            experience='4+ years',
            is_active=True,
        )
        self.job_2 = Job.objects.create(
            employer=self.employer_2,
            title='ML Research Engineer',
            company='DataForge Labs',
            description='Train and deploy recommendation models.',
            location='Remote',
            salary='20-26 LPA',
            job_type=Job.JOB_TYPE_REMOTE,
            skills_required='Python, PyTorch',
            experience='2-4 years',
            is_active=False,
        )

    def test_admin_dashboard_access_control_and_login_redirect(self):
        anon_resp = self.client.get(self.admin_dashboard_url)
        self.assertRedirects(anon_resp, f'{self.login_url}?next={self.admin_dashboard_url}')

        self.client.force_login(self.seeker_1)
        self.assertEqual(self.client.get(self.admin_dashboard_url).status_code, 403)
        self.client.post(reverse('logout'))

        self.client.force_login(self.employer_1)
        self.assertEqual(self.client.get(self.admin_dashboard_url).status_code, 403)
        self.client.post(reverse('logout'))

        login_resp = self.client.post(
            self.login_url,
            {'email': 'portaladmin@example.com', 'password': 'Password#2026'},
        )
        self.assertRedirects(login_resp, self.admin_dashboard_url)

    def test_admin_dashboard_metrics_search_filters_resume_and_status_updates(self):
        pdf_bytes = b'%PDF-1.4\n%Admin Portal Test Resume\n%%EOF'
        with tempfile.TemporaryDirectory() as tmp_media:
            with override_settings(MEDIA_ROOT=tmp_media):
                resume_1 = SimpleUploadedFile('ananya_cv.pdf', pdf_bytes, content_type='application/pdf')
                resume_2 = SimpleUploadedFile('karan_cv.pdf', pdf_bytes, content_type='application/pdf')
                app_1 = JobApplication.objects.create(
                    job=self.job_1,
                    applicant=self.seeker_1,
                    resume=resume_1,
                    cover_note='Excited about distributed Python backends.',
                )
                app_2 = JobApplication.objects.create(
                    job=self.job_2,
                    applicant=self.seeker_2,
                    resume=resume_2,
                    cover_note='Published work in recommender systems.',
                )

                self.client.force_login(self.admin_user)
                dash_resp = self.client.get(self.admin_dashboard_url)
                self.assertEqual(dash_resp.status_code, 200)
                self.assertEqual(dash_resp.context['total_users'], 5)
                self.assertEqual(dash_resp.context['total_employers'], 2)
                self.assertEqual(dash_resp.context['total_job_seekers'], 2)
                self.assertEqual(dash_resp.context['total_staff'], 1)
                self.assertEqual(dash_resp.context['total_jobs'], Job.objects.count())
                self.assertEqual(dash_resp.context['active_jobs_count'], Job.objects.filter(is_active=True).count())
                self.assertEqual(dash_resp.context['inactive_jobs_count'], Job.objects.filter(is_active=False).count())
                self.assertEqual(dash_resp.context['total_jobs'], 8)
                self.assertEqual(dash_resp.context['active_jobs_count'], 7)
                self.assertEqual(dash_resp.context['inactive_jobs_count'], 1)
                self.assertEqual(dash_resp.context['total_applications'], 2)

                self.assertContains(dash_resp, 'Ananya Deshmukh')
                self.assertContains(dash_resp, 'ananya@example.com')
                self.assertContains(dash_resp, 'Karan Malhotra')
                self.assertContains(dash_resp, 'Senior Python Engineer')
                self.assertContains(dash_resp, 'ML Research Engineer')
                self.assertContains(dash_resp, reverse('download_applicant_resume', args=[app_1.id]))
                self.assertContains(dash_resp, reverse('admin:index'))

                # Staff can view inactive job detail directly
                inactive_job_detail = self.client.get(reverse('job_detail', args=[self.job_2.id]))
                self.assertEqual(inactive_job_detail.status_code, 200)

                # Search by applicant name / company
                search_resp = self.client.get(self.admin_dashboard_url, {'q': 'Ananya'})
                self.assertEqual(list(search_resp.context['applications']), [app_1])
                company_search = self.client.get(self.admin_dashboard_url, {'q': 'DataForge'})
                self.assertEqual(list(company_search.context['applications']), [app_2])

                # Job filter and invalid filter guard
                job_filter_resp = self.client.get(self.admin_dashboard_url, {'job': self.job_2.id})
                self.assertEqual(list(job_filter_resp.context['applications']), [app_2])
                bad_job_resp = self.client.get(self.admin_dashboard_url, {'job': 'bad'}, follow=True)
                self.assertRedirects(bad_job_resp, self.admin_dashboard_url)
                self.assertContains(bad_job_resp, 'Invalid job filter specified.')

                # Resume download & inline view work for admin
                dl_resp = self.client.get(reverse('download_applicant_resume', args=[app_1.id]))
                self.assertEqual(dl_resp.status_code, 200)
                self.assertIn('attachment;', dl_resp['Content-Disposition'])
                dl_resp.close()

                inline_resp = self.client.get(
                    f"{reverse('download_applicant_resume', args=[app_1.id])}?inline=1"
                )
                self.assertEqual(inline_resp.status_code, 200)
                self.assertIn('inline;', inline_resp['Content-Disposition'])
                inline_resp.close()

                # Update status across workflow steps as admin
                status_url_1 = reverse('update_application_status', args=[app_1.id])
                upd_shortlist = self.client.post(
                    status_url_1,
                    {'status': JobApplication.STATUS_SHORTLISTED, 'next': self.admin_dashboard_url},
                    follow=True,
                )
                self.assertRedirects(upd_shortlist, self.admin_dashboard_url)
                self.assertContains(upd_shortlist, 'updated to Shortlisted')

                upd_select = self.client.post(
                    status_url_1,
                    {'status': JobApplication.STATUS_SELECTED},
                    follow=True,
                )
                self.assertRedirects(upd_select, self.admin_dashboard_url)

                status_url_2 = reverse('update_application_status', args=[app_2.id])
                upd_reject = self.client.post(
                    status_url_2,
                    {'status': JobApplication.STATUS_REJECTED, 'next': self.admin_dashboard_url},
                    follow=True,
                )
                self.assertRedirects(upd_reject, self.admin_dashboard_url)

                # Invalid status value is rejected cleanly
                invalid_status_post = self.client.post(
                    status_url_1,
                    {'status': 'invalid_state', 'next': self.admin_dashboard_url},
                    follow=True,
                )
                self.assertRedirects(invalid_status_post, self.admin_dashboard_url)
                self.assertContains(invalid_status_post, 'Please select a valid application status.')

                app_1.refresh_from_db()
                app_2.refresh_from_db()
                self.assertEqual(app_1.status, JobApplication.STATUS_SELECTED)
                self.assertEqual(app_2.status, JobApplication.STATUS_REJECTED)
                self.assertEqual(
                    list(app_1.status_history.values_list('status', flat=True)),
                    [
                        JobApplication.STATUS_APPLIED,
                        JobApplication.STATUS_SHORTLISTED,
                        JobApplication.STATUS_SELECTED,
                    ],
                )
                self.assertEqual(app_1.status_history.last().changed_by, self.admin_user)

                # Filter by status and combine q + status filters
                selected_resp = self.client.get(
                    self.admin_dashboard_url,
                    {'status': JobApplication.STATUS_SELECTED},
                )
                self.assertEqual(list(selected_resp.context['applications']), [app_1])

                bad_status = self.client.get(
                    self.admin_dashboard_url,
                    {'status': 'unknown'},
                    follow=True,
                )
                self.assertRedirects(bad_status, self.admin_dashboard_url)
                self.assertContains(bad_status, 'Invalid application status filter specified.')

                # Verify updated status appears on Job Seeker Dashboard
                self.client.post(reverse('logout'))
                self.client.force_login(self.seeker_1)
                seeker_dash = self.client.get(reverse('job_seeker_dashboard'))
                self.assertContains(seeker_dash, 'Selected')
                self.assertContains(seeker_dash, 'Shortlisted')
