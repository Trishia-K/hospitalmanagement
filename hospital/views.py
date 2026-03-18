import logging
import io

from django.shortcuts import render, redirect, reverse
from . import forms, models
from django.db.models import Sum
from django.contrib.auth.models import Group
from django.http import HttpResponseRedirect, HttpResponse
from django.core.mail import send_mail
from django.contrib.auth.decorators import login_required, user_passes_test
from datetime import datetime, timedelta, date
from django.conf import settings
from django.db.models import Q
from django.core.exceptions import ObjectDoesNotExist
from xhtml2pdf import pisa
from django.template.loader import get_template

# Logging setup
logger = logging.getLogger(__name__)


# Helper checks 
def is_admin(user):
    return user.groups.filter(name='ADMIN').exists()

def is_doctor(user):
    return user.groups.filter(name='DOCTOR').exists()

def is_patient(user):
    return user.groups.filter(name='PATIENT').exists()


# Public views
def home_view(request):
    if request.user.is_authenticated:
        return HttpResponseRedirect('afterlogin')
    return render(request, 'hospital/index.html')


def adminclick_view(request):
    if request.user.is_authenticated:
        return HttpResponseRedirect('afterlogin')
    return render(request, 'hospital/adminclick.html')


def doctorclick_view(request):
    if request.user.is_authenticated:
        return HttpResponseRedirect('afterlogin')
    return render(request, 'hospital/doctorclick.html')


def patientclick_view(request):
    if request.user.is_authenticated:
        return HttpResponseRedirect('afterlogin')
    return render(request, 'hospital/patientclick.html')


#Signup views
def admin_signup_view(request):
    form = forms.AdminSigupForm()
    if request.method == 'POST':
        form = forms.AdminSigupForm(request.POST)
        if form.is_valid():
            try:
                user = form.save()
                user.set_password(user.password)
                user.save()
                my_admin_group = Group.objects.get_or_create(name='ADMIN')
                my_admin_group[0].user_set.add(user)
                logger.info(f"New admin account created: {user.username}")
                return HttpResponseRedirect('adminlogin')
            except Exception as e:
                logger.error(f"Error creating admin account: {e}")
                return render(request, 'hospital/adminsignup.html', {'form': form, 'error': 'Account creation failed. Please try again.'})
    return render(request, 'hospital/adminsignup.html', {'form': form})


def doctor_signup_view(request):
    userForm = forms.DoctorUserForm()
    doctorForm = forms.DoctorForm()
    mydict = {'userForm': userForm, 'doctorForm': doctorForm}
    if request.method == 'POST':
        userForm = forms.DoctorUserForm(request.POST)
        doctorForm = forms.DoctorForm(request.POST, request.FILES)
        if userForm.is_valid() and doctorForm.is_valid():
            try:
                user = userForm.save()
                user.set_password(user.password)
                user.save()
                doctor = doctorForm.save(commit=False)
                doctor.user = user
                doctor.save()
                my_doctor_group = Group.objects.get_or_create(name='DOCTOR')
                my_doctor_group[0].user_set.add(user)
                logger.info(f"New doctor account created: {user.username}")
            except Exception as e:
                logger.error(f"Error creating doctor account: {e}")
        return HttpResponseRedirect('doctorlogin')
    return render(request, 'hospital/doctorsignup.html', context=mydict)


def patient_signup_view(request):
    userForm = forms.PatientUserForm()
    patientForm = forms.PatientForm()
    mydict = {'userForm': userForm, 'patientForm': patientForm}
    if request.method == 'POST':
        userForm = forms.PatientUserForm(request.POST)
        patientForm = forms.PatientForm(request.POST, request.FILES)
        if userForm.is_valid() and patientForm.is_valid():
            try:
                user = userForm.save()
                user.set_password(user.password)
                user.save()
                patient = patientForm.save(commit=False)
                patient.user = user
                patient.assignedDoctorId = request.POST.get('assignedDoctorId')
                patient.save()
                my_patient_group = Group.objects.get_or_create(name='PATIENT')
                my_patient_group[0].user_set.add(user)
                logger.info(f"New patient account created: {user.username}")
            except Exception as e:
                logger.error(f"Error creating patient account: {e}")
        return HttpResponseRedirect('patientlogin')
    return render(request, 'hospital/patientsignup.html', context=mydict)


# After login routing
def afterlogin_view(request):
    if is_admin(request.user):
        return redirect('admin-dashboard')
    elif is_doctor(request.user):
        accountapproval = models.Doctor.objects.all().filter(user_id=request.user.id, status=True)
        if accountapproval:
            return redirect('doctor-dashboard')
        else:
            return render(request, 'hospital/doctor_wait_for_approval.html')
    elif is_patient(request.user):
        accountapproval = models.Patient.objects.all().filter(user_id=request.user.id, status=True)
        if accountapproval:
            return redirect('patient-dashboard')
        else:
            return render(request, 'hospital/patient_wait_for_approval.html')


#Admin views
@login_required(login_url='adminlogin')
@user_passes_test(is_admin)
def admin_dashboard_view(request):
    try:
        doctors = models.Doctor.objects.all().order_by('-id')
        patients = models.Patient.objects.all().order_by('-id')
        doctorcount = models.Doctor.objects.all().filter(status=True).count()
        pendingdoctorcount = models.Doctor.objects.all().filter(status=False).count()
        patientcount = models.Patient.objects.all().filter(status=True).count()
        pendingpatientcount = models.Patient.objects.all().filter(status=False).count()
        appointmentcount = models.Appointment.objects.all().filter(status=True).count()
        pendingappointmentcount = models.Appointment.objects.all().filter(status=False).count()
        mydict = {
            'doctors': doctors,
            'patients': patients,
            'doctorcount': doctorcount,
            'pendingdoctorcount': pendingdoctorcount,
            'patientcount': patientcount,
            'pendingpatientcount': pendingpatientcount,
            'appointmentcount': appointmentcount,
            'pendingappointmentcount': pendingappointmentcount,
        }
        logger.info("Admin dashboard loaded successfully")
        return render(request, 'hospital/admin_dashboard.html', context=mydict)
    except Exception as e:
        logger.error(f"Error loading admin dashboard: {e}")
        return render(request, 'hospital/admin_dashboard.html', {})


@login_required(login_url='adminlogin')
@user_passes_test(is_admin)
def admin_doctor_view(request):
    return render(request, 'hospital/admin_doctor.html')


@login_required(login_url='adminlogin')
@user_passes_test(is_admin)
def admin_view_doctor_view(request):
    doctors = models.Doctor.objects.all().filter(status=True)
    return render(request, 'hospital/admin_view_doctor.html', {'doctors': doctors})


@login_required(login_url='adminlogin')
@user_passes_test(is_admin)
def delete_doctor_from_hospital_view(request, pk):
    # IMPROVED: was missing try/except — .get() crashes if ID doesn't exist
    try:
        doctor = models.Doctor.objects.get(id=pk)
        user = models.User.objects.get(id=doctor.user_id)
        user.delete()
        doctor.delete()
        logger.info(f"Doctor with ID {pk} deleted by admin {request.user.username}")
    except ObjectDoesNotExist:
        logger.warning(f"Attempted to delete non-existent doctor with ID {pk}")
    except Exception as e:
        logger.error(f"Error deleting doctor ID {pk}: {e}")
    return redirect('admin-view-doctor')


@login_required(login_url='adminlogin')
@user_passes_test(is_admin)
def update_doctor_view(request, pk):
    # IMPROVED: was missing try/except — .get() crashes if ID doesn't exist
    try:
        doctor = models.Doctor.objects.get(id=pk)
        user = models.User.objects.get(id=doctor.user_id)
    except ObjectDoesNotExist:
        logger.warning(f"Update attempted for non-existent doctor ID {pk}")
        return redirect('admin-view-doctor')

    userForm = forms.DoctorUserForm(instance=user)
    doctorForm = forms.DoctorForm(request.FILES, instance=doctor)
    mydict = {'userForm': userForm, 'doctorForm': doctorForm}
    if request.method == 'POST':
        userForm = forms.DoctorUserForm(request.POST, instance=user)
        doctorForm = forms.DoctorForm(request.POST, request.FILES, instance=doctor)
        if userForm.is_valid() and doctorForm.is_valid():
            try:
                user = userForm.save()
                user.set_password(user.password)
                user.save()
                doctor = doctorForm.save(commit=False)
                doctor.status = True
                doctor.save()
                logger.info(f"Doctor ID {pk} updated by admin {request.user.username}")
                return redirect('admin-view-doctor')
            except Exception as e:
                logger.error(f"Error updating doctor ID {pk}: {e}")
    return render(request, 'hospital/admin_update_doctor.html', context=mydict)


@login_required(login_url='adminlogin')
@user_passes_test(is_admin)
def admin_add_doctor_view(request):
    userForm = forms.DoctorUserForm()
    doctorForm = forms.DoctorForm()
    mydict = {'userForm': userForm, 'doctorForm': doctorForm}
    if request.method == 'POST':
        userForm = forms.DoctorUserForm(request.POST)
        doctorForm = forms.DoctorForm(request.POST, request.FILES)
        if userForm.is_valid() and doctorForm.is_valid():
            try:
                user = userForm.save()
                user.set_password(user.password)
                user.save()
                doctor = doctorForm.save(commit=False)
                doctor.user = user
                doctor.status = True
                doctor.save()
                my_doctor_group = Group.objects.get_or_create(name='DOCTOR')
                my_doctor_group[0].user_set.add(user)
                logger.info(f"Doctor added by admin: {user.username}")
            except Exception as e:
                logger.error(f"Error adding doctor: {e}")
        return HttpResponseRedirect('admin-view-doctor')
    return render(request, 'hospital/admin_add_doctor.html', context=mydict)


@login_required(login_url='adminlogin')
@user_passes_test(is_admin)
def admin_approve_doctor_view(request):
    doctors = models.Doctor.objects.all().filter(status=False)
    return render(request, 'hospital/admin_approve_doctor.html', {'doctors': doctors})


@login_required(login_url='adminlogin')
@user_passes_test(is_admin)
def approve_doctor_view(request, pk):
    try:
        doctor = models.Doctor.objects.get(id=pk)
        doctor.status = True
        doctor.save()
        logger.info(f"Doctor ID {pk} approved by admin {request.user.username}")
    except ObjectDoesNotExist:
        logger.warning(f"Approval attempted for non-existent doctor ID {pk}")
    return redirect(reverse('admin-approve-doctor'))


@login_required(login_url='adminlogin')
@user_passes_test(is_admin)
def reject_doctor_view(request, pk):
    try:
        doctor = models.Doctor.objects.get(id=pk)
        user = models.User.objects.get(id=doctor.user_id)
        user.delete()
        doctor.delete()
        logger.info(f"Doctor ID {pk} rejected and removed by admin {request.user.username}")
    except ObjectDoesNotExist:
        logger.warning(f"Rejection attempted for non-existent doctor ID {pk}")
    except Exception as e:
        logger.error(f"Error rejecting doctor ID {pk}: {e}")
    return redirect('admin-approve-doctor')


@login_required(login_url='adminlogin')
@user_passes_test(is_admin)
def admin_view_doctor_specialisation_view(request):
    doctors = models.Doctor.objects.all().filter(status=True)
    return render(request, 'hospital/admin_view_doctor_specialisation.html', {'doctors': doctors})


@login_required(login_url='adminlogin')
@user_passes_test(is_admin)
def admin_patient_view(request):
    return render(request, 'hospital/admin_patient.html')


@login_required(login_url='adminlogin')
@user_passes_test(is_admin)
def admin_view_patient_view(request):
    patients = models.Patient.objects.all().filter(status=True)
    return render(request, 'hospital/admin_view_patient.html', {'patients': patients})


@login_required(login_url='adminlogin')
@user_passes_test(is_admin)
def delete_patient_from_hospital_view(request, pk):
    # IMPROVED: was missing try/except — .get() crashes if ID doesn't exist
    try:
        patient = models.Patient.objects.get(id=pk)
        user = models.User.objects.get(id=patient.user_id)
        user.delete()
        patient.delete()
        logger.info(f"Patient ID {pk} deleted by admin {request.user.username}")
    except ObjectDoesNotExist:
        logger.warning(f"Attempted to delete non-existent patient ID {pk}")
    except Exception as e:
        logger.error(f"Error deleting patient ID {pk}: {e}")
    return redirect('admin-view-patient')


@login_required(login_url='adminlogin')
@user_passes_test(is_admin)
def update_patient_view(request, pk):
    # IMPROVED: was missing try/except — .get() crashes if ID doesn't exist
    try:
        patient = models.Patient.objects.get(id=pk)
        user = models.User.objects.get(id=patient.user_id)
    except ObjectDoesNotExist:
        logger.warning(f"Update attempted for non-existent patient ID {pk}")
        return redirect('admin-view-patient')

    userForm = forms.PatientUserForm(instance=user)
    patientForm = forms.PatientForm(request.FILES, instance=patient)
    mydict = {'userForm': userForm, 'patientForm': patientForm}
    if request.method == 'POST':
        userForm = forms.PatientUserForm(request.POST, instance=user)
        patientForm = forms.PatientForm(request.POST, request.FILES, instance=patient)
        if userForm.is_valid() and patientForm.is_valid():
            try:
                user = userForm.save()
                user.set_password(user.password)
                user.save()
                patient = patientForm.save(commit=False)
                patient.status = True
                patient.assignedDoctorId = request.POST.get('assignedDoctorId')
                patient.save()
                logger.info(f"Patient ID {pk} updated by admin {request.user.username}")
                return redirect('admin-view-patient')
            except Exception as e:
                logger.error(f"Error updating patient ID {pk}: {e}")
    return render(request, 'hospital/admin_update_patient.html', context=mydict)


@login_required(login_url='adminlogin')
@user_passes_test(is_admin)
def admin_add_patient_view(request):
    userForm = forms.PatientUserForm()
    patientForm = forms.PatientForm()
    mydict = {'userForm': userForm, 'patientForm': patientForm}
    if request.method == 'POST':
        userForm = forms.PatientUserForm(request.POST)
        patientForm = forms.PatientForm(request.POST, request.FILES)
        if userForm.is_valid() and patientForm.is_valid():
            try:
                user = userForm.save()
                user.set_password(user.password)
                user.save()
                patient = patientForm.save(commit=False)
                patient.user = user
                patient.status = True
                patient.assignedDoctorId = request.POST.get('assignedDoctorId')
                patient.save()
                my_patient_group = Group.objects.get_or_create(name='PATIENT')
                my_patient_group[0].user_set.add(user)
                logger.info(f"Patient added by admin: {user.username}")
            except Exception as e:
                logger.error(f"Error adding patient: {e}")
        return HttpResponseRedirect('admin-view-patient')
    return render(request, 'hospital/admin_add_patient.html', context=mydict)


@login_required(login_url='adminlogin')
@user_passes_test(is_admin)
def admin_approve_patient_view(request):
    patients = models.Patient.objects.all().filter(status=False)
    return render(request, 'hospital/admin_approve_patient.html', {'patients': patients})


@login_required(login_url='adminlogin')
@user_passes_test(is_admin)
def approve_patient_view(request, pk):
    try:
        patient = models.Patient.objects.get(id=pk)
        patient.status = True
        patient.save()
        logger.info(f"Patient ID {pk} approved by admin {request.user.username}")
    except ObjectDoesNotExist:
        logger.warning(f"Approval attempted for non-existent patient ID {pk}")
    return redirect(reverse('admin-approve-patient'))


@login_required(login_url='adminlogin')
@user_passes_test(is_admin)
def reject_patient_view(request, pk):
    try:
        patient = models.Patient.objects.get(id=pk)
        user = models.User.objects.get(id=patient.user_id)
        user.delete()
        patient.delete()
        logger.info(f"Patient ID {pk} rejected by admin {request.user.username}")
    except ObjectDoesNotExist:
        logger.warning(f"Rejection attempted for non-existent patient ID {pk}")
    except Exception as e:
        logger.error(f"Error rejecting patient ID {pk}: {e}")
    return redirect('admin-approve-patient')


@login_required(login_url='adminlogin')
@user_passes_test(is_admin)
def admin_discharge_patient_view(request):
    patients = models.Patient.objects.all().filter(status=True)
    return render(request, 'hospital/admin_discharge_patient.html', {'patients': patients})


@login_required(login_url='adminlogin')
@user_passes_test(is_admin)
def discharge_patient_view(request, pk):
    # IMPROVED: added try/except around .get() and int() conversions
    try:
        patient = models.Patient.objects.get(id=pk)
    except ObjectDoesNotExist:
        logger.warning(f"Discharge attempted for non-existent patient ID {pk}")
        return redirect('admin-discharge-patient')

    days = (date.today() - patient.admitDate)
    assignedDoctor = models.User.objects.all().filter(id=patient.assignedDoctorId)
    d = days.days
    patientDict = {
        'patientId': pk,
        'name': patient.get_name,
        'mobile': patient.mobile,
        'address': patient.address,
        'symptoms': patient.symptoms,
        'admitDate': patient.admitDate,
        'todayDate': date.today(),
        'day': d,
        'assignedDoctorName': assignedDoctor[0].first_name if assignedDoctor else 'Unknown',
    }
    if request.method == 'POST':
        # IMPROVED: validate and safely convert all fee fields
        try:
            room_charge = int(request.POST.get('roomCharge', 0))
            doctor_fee = int(request.POST.get('doctorFee', 0))
            medicine_cost = int(request.POST.get('medicineCost', 0))
            other_charge = int(request.POST.get('OtherCharge', 0))
        except ValueError as e:
            logger.warning(f"Invalid fee input for patient ID {pk}: {e}")
            return render(request, 'hospital/patient_generate_bill.html', {
                **patientDict, 'error': 'Please enter valid numbers for all charges.'
            })

        feeDict = {
            'roomCharge': room_charge * int(d),
            'doctorFee': doctor_fee,
            'medicineCost': medicine_cost,
            'OtherCharge': other_charge,
            'total': (room_charge * int(d)) + doctor_fee + medicine_cost + other_charge
        }
        patientDict.update(feeDict)
        try:
            pDD = models.PatientDischargeDetails()
            pDD.patientId = pk
            pDD.patientName = patient.get_name
            pDD.assignedDoctorName = assignedDoctor[0].first_name if assignedDoctor else 'Unknown'
            pDD.address = patient.address
            pDD.mobile = patient.mobile
            pDD.symptoms = patient.symptoms
            pDD.admitDate = patient.admitDate
            pDD.releaseDate = date.today()
            pDD.daySpent = int(d)
            pDD.medicineCost = medicine_cost
            pDD.roomCharge = room_charge * int(d)
            pDD.doctorFee = doctor_fee
            pDD.OtherCharge = other_charge
            pDD.total = feeDict['total']
            pDD.save()
            logger.info(f"Patient ID {pk} discharged. Total bill: {feeDict['total']}")
        except Exception as e:
            logger.error(f"Error saving discharge details for patient ID {pk}: {e}")
        return render(request, 'hospital/patient_final_bill.html', context=patientDict)
    return render(request, 'hospital/patient_generate_bill.html', context=patientDict)


# PDF generation
def render_to_pdf(template_src, context_dict):
    # IMPROVED: now returns a proper error response instead of None
    try:
        template = get_template(template_src)
        html = template.render(context_dict)
        result = io.BytesIO()
        pdf = pisa.pisaDocument(io.BytesIO(html.encode("ISO-8859-1")), result)
        if not pdf.err:
            logger.info(f"PDF generated successfully from template: {template_src}")
            return HttpResponse(result.getvalue(), content_type='application/pdf')
        else:
            logger.error(f"PDF generation failed with errors: {pdf.err}")
            return HttpResponse("PDF generation failed. Please try again.", status=500)
    except Exception as e:
        logger.error(f"Unexpected error in render_to_pdf: {e}")
        return HttpResponse("An error occurred generating the PDF.", status=500)


def download_pdf_view(request, pk):
    # IMPROVED: was crashing with IndexError if no discharge record exists
    try:
        dischargeDetails = models.PatientDischargeDetails.objects.all().filter(
            patientId=pk).order_by('-id')[:1]
        if not dischargeDetails:
            logger.warning(f"PDF download attempted but no discharge record found for patient ID {pk}")
            return HttpResponse("No discharge record found for this patient.", status=404)

        bill_dict = {
            'patientName': dischargeDetails[0].patientName,
            'assignedDoctorName': dischargeDetails[0].assignedDoctorName,
            'address': dischargeDetails[0].address,
            'mobile': dischargeDetails[0].mobile,
            'symptoms': dischargeDetails[0].symptoms,
            'admitDate': dischargeDetails[0].admitDate,
            'releaseDate': dischargeDetails[0].releaseDate,
            'daySpent': dischargeDetails[0].daySpent,
            'medicineCost': dischargeDetails[0].medicineCost,
            'roomCharge': dischargeDetails[0].roomCharge,
            'doctorFee': dischargeDetails[0].doctorFee,
            'OtherCharge': dischargeDetails[0].OtherCharge,
            'total': dischargeDetails[0].total,
        }
        logger.info(f"PDF bill downloaded for patient ID {pk}")
        return render_to_pdf('hospital/download_bill.html', bill_dict)
    except Exception as e:
        logger.error(f"Error generating PDF for patient ID {pk}: {e}")
        return HttpResponse("Error generating bill. Please try again.", status=500)


#Admin appointment views 
@login_required(login_url='adminlogin')
@user_passes_test(is_admin)
def admin_appointment_view(request):
    return render(request, 'hospital/admin_appointment.html')


@login_required(login_url='adminlogin')
@user_passes_test(is_admin)
def admin_view_appointment_view(request):
    appointments = models.Appointment.objects.all().filter(status=True)
    return render(request, 'hospital/admin_view_appointment.html', {'appointments': appointments})


@login_required(login_url='adminlogin')
@user_passes_test(is_admin)
def admin_add_appointment_view(request):
    appointmentForm = forms.AppointmentForm()
    mydict = {'appointmentForm': appointmentForm}
    if request.method == 'POST':
        appointmentForm = forms.AppointmentForm(request.POST)
        if appointmentForm.is_valid():
            try:
                appointment = appointmentForm.save(commit=False)
                appointment.doctorId = request.POST.get('doctorId')
                appointment.patientId = request.POST.get('patientId')
                appointment.doctorName = models.User.objects.get(
                    id=request.POST.get('doctorId')).first_name
                appointment.patientName = models.User.objects.get(
                    id=request.POST.get('patientId')).first_name
                appointment.status = True
                appointment.save()
                logger.info(f"Appointment added by admin for doctor ID {appointment.doctorId}")
            except ObjectDoesNotExist as e:
                logger.warning(f"Appointment creation failed — doctor or patient not found: {e}")
            except Exception as e:
                logger.error(f"Error creating appointment: {e}")
        return HttpResponseRedirect('admin-view-appointment')
    return render(request, 'hospital/admin_add_appointment.html', context=mydict)


@login_required(login_url='adminlogin')
@user_passes_test(is_admin)
def admin_approve_appointment_view(request):
    appointments = models.Appointment.objects.all().filter(status=False)
    return render(request, 'hospital/admin_approve_appointment.html', {'appointments': appointments})


@login_required(login_url='adminlogin')
@user_passes_test(is_admin)
def approve_appointment_view(request, pk):
    try:
        appointment = models.Appointment.objects.get(id=pk)
        appointment.status = True
        appointment.save()
        logger.info(f"Appointment ID {pk} approved by admin {request.user.username}")
    except ObjectDoesNotExist:
        logger.warning(f"Approval attempted for non-existent appointment ID {pk}")
    return redirect(reverse('admin-approve-appointment'))


@login_required(login_url='adminlogin')
@user_passes_test(is_admin)
def reject_appointment_view(request, pk):
    try:
        appointment = models.Appointment.objects.get(id=pk)
        appointment.delete()
        logger.info(f"Appointment ID {pk} rejected by admin {request.user.username}")
    except ObjectDoesNotExist:
        logger.warning(f"Rejection attempted for non-existent appointment ID {pk}")
    return redirect('admin-approve-appointment')


#Doctor views
@login_required(login_url='doctorlogin')
@user_passes_test(is_doctor)
def doctor_dashboard_view(request):
    try:
        patientcount = models.Patient.objects.all().filter(
            status=True, assignedDoctorId=request.user.id).count()
        appointmentcount = models.Appointment.objects.all().filter(
            status=True, doctorId=request.user.id).count()
        patientdischarged = models.PatientDischargeDetails.objects.all().distinct().filter(
            assignedDoctorName=request.user.first_name).count()
        appointments = models.Appointment.objects.all().filter(
            status=True, doctorId=request.user.id).order_by('-id')
        patientid = [a.patientId for a in appointments]
        patients = models.Patient.objects.all().filter(
            status=True, user_id__in=patientid).order_by('-id')
        appointments = zip(appointments, patients)
        mydict = {
            'patientcount': patientcount,
            'appointmentcount': appointmentcount,
            'patientdischarged': patientdischarged,
            'appointments': appointments,
            'doctor': models.Doctor.objects.get(user_id=request.user.id),
        }
        logger.info(f"Doctor dashboard loaded for {request.user.username}")
        return render(request, 'hospital/doctor_dashboard.html', context=mydict)
    except ObjectDoesNotExist:
        logger.warning(f"Doctor profile not found for user ID {request.user.id}")
        return render(request, 'hospital/doctor_dashboard.html', {})
    except Exception as e:
        logger.error(f"Error loading doctor dashboard for {request.user.username}: {e}")
        return render(request, 'hospital/doctor_dashboard.html', {})


@login_required(login_url='doctorlogin')
@user_passes_test(is_doctor)
def doctor_patient_view(request):
    try:
        doctor = models.Doctor.objects.get(user_id=request.user.id)
        return render(request, 'hospital/doctor_patient.html', {'doctor': doctor})
    except ObjectDoesNotExist:
        logger.warning(f"Doctor profile not found for user {request.user.username}")
        return render(request, 'hospital/doctor_patient.html', {})


@login_required(login_url='doctorlogin')
@user_passes_test(is_doctor)
def doctor_view_patient_view(request):
    try:
        patients = models.Patient.objects.all().filter(
            status=True, assignedDoctorId=request.user.id)
        doctor = models.Doctor.objects.get(user_id=request.user.id)
        return render(request, 'hospital/doctor_view_patient.html',
                      {'patients': patients, 'doctor': doctor})
    except ObjectDoesNotExist:
        logger.warning(f"Doctor profile not found for user {request.user.username}")
        return redirect('doctor-dashboard')


@login_required(login_url='doctorlogin')
@user_passes_test(is_doctor)
def search_view(request):
    try:
        doctor = models.Doctor.objects.get(user_id=request.user.id)
        query = request.GET.get('query', '').strip()
        if not query:
            logger.warning(f"Empty search query submitted by doctor {request.user.username}")
            return redirect('doctor-view-patient')
        patients = models.Patient.objects.all().filter(
            status=True, assignedDoctorId=request.user.id
        ).filter(Q(symptoms__icontains=query) | Q(user__first_name__icontains=query))
        logger.info(f"Doctor {request.user.username} searched for '{query}', found {patients.count()} results")
        return render(request, 'hospital/doctor_view_patient.html',
                      {'patients': patients, 'doctor': doctor})
    except ObjectDoesNotExist:
        logger.warning(f"Doctor profile not found for user {request.user.username}")
        return redirect('doctor-dashboard')


@login_required(login_url='doctorlogin')
@user_passes_test(is_doctor)
def doctor_view_discharge_patient_view(request):
    try:
        dischargedpatients = models.PatientDischargeDetails.objects.all().distinct().filter(
            assignedDoctorName=request.user.first_name)
        doctor = models.Doctor.objects.get(user_id=request.user.id)
        return render(request, 'hospital/doctor_view_discharge_patient.html',
                      {'dischargedpatients': dischargedpatients, 'doctor': doctor})
    except ObjectDoesNotExist:
        logger.warning(f"Doctor profile not found for user {request.user.username}")
        return redirect('doctor-dashboard')


@login_required(login_url='doctorlogin')
@user_passes_test(is_doctor)
def doctor_appointment_view(request):
    try:
        doctor = models.Doctor.objects.get(user_id=request.user.id)
        return render(request, 'hospital/doctor_appointment.html', {'doctor': doctor})
    except ObjectDoesNotExist:
        logger.warning(f"Doctor profile not found for user {request.user.username}")
        return redirect('doctor-dashboard')


@login_required(login_url='doctorlogin')
@user_passes_test(is_doctor)
def doctor_view_appointment_view(request):
    try:
        doctor = models.Doctor.objects.get(user_id=request.user.id)
        appointments = models.Appointment.objects.all().filter(
            status=True, doctorId=request.user.id)
        patientid = [a.patientId for a in appointments]
        patients = models.Patient.objects.all().filter(status=True, user_id__in=patientid)
        appointments = zip(appointments, patients)
        return render(request, 'hospital/doctor_view_appointment.html',
                      {'appointments': appointments, 'doctor': doctor})
    except ObjectDoesNotExist:
        logger.warning(f"Doctor profile not found for user {request.user.username}")
        return redirect('doctor-dashboard')


@login_required(login_url='doctorlogin')
@user_passes_test(is_doctor)
def doctor_delete_appointment_view(request):
    try:
        doctor = models.Doctor.objects.get(user_id=request.user.id)
        appointments = models.Appointment.objects.all().filter(
            status=True, doctorId=request.user.id)
        patientid = [a.patientId for a in appointments]
        patients = models.Patient.objects.all().filter(status=True, user_id__in=patientid)
        appointments = zip(appointments, patients)
        return render(request, 'hospital/doctor_delete_appointment.html',
                      {'appointments': appointments, 'doctor': doctor})
    except ObjectDoesNotExist:
        logger.warning(f"Doctor profile not found for user {request.user.username}")
        return redirect('doctor-dashboard')


@login_required(login_url='doctorlogin')
@user_passes_test(is_doctor)
def delete_appointment_view(request, pk):
    try:
        appointment = models.Appointment.objects.get(id=pk)
        appointment.delete()
        logger.info(f"Appointment ID {pk} deleted by doctor {request.user.username}")
    except ObjectDoesNotExist:
        logger.warning(f"Delete attempted for non-existent appointment ID {pk}")

    try:
        doctor = models.Doctor.objects.get(user_id=request.user.id)
        appointments = models.Appointment.objects.all().filter(
            status=True, doctorId=request.user.id)
        patientid = [a.patientId for a in appointments]
        patients = models.Patient.objects.all().filter(status=True, user_id__in=patientid)
        appointments = zip(appointments, patients)
        return render(request, 'hospital/doctor_delete_appointment.html',
                      {'appointments': appointments, 'doctor': doctor})
    except ObjectDoesNotExist:
        logger.warning(f"Doctor profile not found for user {request.user.username}")
        return redirect('doctor-dashboard')


#Patient views
@login_required(login_url='patientlogin')
@user_passes_test(is_patient)
def patient_dashboard_view(request):
    try:
        patient = models.Patient.objects.get(user_id=request.user.id)
        doctor = models.Doctor.objects.get(user_id=patient.assignedDoctorId)
        mydict = {
            'patient': patient,
            'doctorName': doctor.get_name,
            'doctorMobile': doctor.mobile,
            'doctorAddress': doctor.address,
            'symptoms': patient.symptoms,
            'doctorDepartment': doctor.department,
            'admitDate': patient.admitDate,
        }
        logger.info(f"Patient dashboard loaded for {request.user.username}")
        return render(request, 'hospital/patient_dashboard.html', context=mydict)
    except ObjectDoesNotExist:
        logger.warning(f"Patient or assigned doctor not found for user {request.user.username}")
        return render(request, 'hospital/patient_dashboard.html', {})
    except Exception as e:
        logger.error(f"Error loading patient dashboard for {request.user.username}: {e}")
        return render(request, 'hospital/patient_dashboard.html', {})


@login_required(login_url='patientlogin')
@user_passes_test(is_patient)
def patient_appointment_view(request):
    try:
        patient = models.Patient.objects.get(user_id=request.user.id)
        return render(request, 'hospital/patient_appointment.html', {'patient': patient})
    except ObjectDoesNotExist:
        logger.warning(f"Patient profile not found for user {request.user.username}")
        return redirect('patient-dashboard')


@login_required(login_url='patientlogin')
@user_passes_test(is_patient)
def patient_book_appointment_view(request):
    try:
        patient = models.Patient.objects.get(user_id=request.user.id)
    except ObjectDoesNotExist:
        logger.warning(f"Patient profile not found for user {request.user.username}")
        return redirect('patient-dashboard')

    appointmentForm = forms.PatientAppointmentForm()
    message = None
    mydict = {'appointmentForm': appointmentForm, 'patient': patient, 'message': message}
    if request.method == 'POST':
        appointmentForm = forms.PatientAppointmentForm(request.POST)
        if appointmentForm.is_valid():
            try:
                appointment = appointmentForm.save(commit=False)
                appointment.doctorId = request.POST.get('doctorId')
                appointment.patientId = request.user.id
                appointment.doctorName = models.User.objects.get(
                    id=request.POST.get('doctorId')).first_name
                appointment.patientName = request.user.first_name
                appointment.status = False
                appointment.save()
                logger.info(f"Appointment booked by patient {request.user.username} "
                            f"with doctor ID {appointment.doctorId}")
            except ObjectDoesNotExist as e:
                logger.warning(f"Appointment booking failed — doctor not found: {e}")
            except Exception as e:
                logger.error(f"Error booking appointment for {request.user.username}: {e}")
        return HttpResponseRedirect('patient-view-appointment')
    return render(request, 'hospital/patient_book_appointment.html', context=mydict)


def patient_view_doctor_view(request):
    try:
        doctors = models.Doctor.objects.all().filter(status=True)
        patient = models.Patient.objects.get(user_id=request.user.id)
        return render(request, 'hospital/patient_view_doctor.html',
                      {'patient': patient, 'doctors': doctors})
    except ObjectDoesNotExist:
        logger.warning(f"Patient profile not found for user {request.user.username}")
        return redirect('patient-dashboard')


def search_doctor_view(request):
    try:
        patient = models.Patient.objects.get(user_id=request.user.id)
        query = request.GET.get('query', '').strip()
        if not query:
            logger.warning(f"Empty doctor search submitted by patient {request.user.username}")
            return redirect('patient-view-doctor')
        doctors = models.Doctor.objects.all().filter(status=True).filter(
            Q(department__icontains=query) | Q(user__first_name__icontains=query))
        logger.info(f"Patient {request.user.username} searched doctors for '{query}'")
        return render(request, 'hospital/patient_view_doctor.html',
                      {'patient': patient, 'doctors': doctors})
    except ObjectDoesNotExist:
        logger.warning(f"Patient profile not found for user {request.user.username}")
        return redirect('patient-dashboard')


@login_required(login_url='patientlogin')
@user_passes_test(is_patient)
def patient_view_appointment_view(request):
    try:
        patient = models.Patient.objects.get(user_id=request.user.id)
        appointments = models.Appointment.objects.all().filter(patientId=request.user.id)
        return render(request, 'hospital/patient_view_appointment.html',
                      {'appointments': appointments, 'patient': patient})
    except ObjectDoesNotExist:
        logger.warning(f"Patient profile not found for user {request.user.username}")
        return redirect('patient-dashboard')


@login_required(login_url='patientlogin')
@user_passes_test(is_patient)
def patient_discharge_view(request):
    try:
        patient = models.Patient.objects.get(user_id=request.user.id)
    except ObjectDoesNotExist:
        logger.warning(f"Patient profile not found for user {request.user.username}")
        return redirect('patient-dashboard')

    try:
        dischargeDetails = models.PatientDischargeDetails.objects.all().filter(
            patientId=patient.id).order_by('-id')[:1]
        if dischargeDetails:
            patientDict = {
                'is_discharged': True,
                'patient': patient,
                'patientId': patient.id,
                'patientName': patient.get_name,
                'assignedDoctorName': dischargeDetails[0].assignedDoctorName,
                'address': patient.address,
                'mobile': patient.mobile,
                'symptoms': patient.symptoms,
                'admitDate': patient.admitDate,
                'releaseDate': dischargeDetails[0].releaseDate,
                'daySpent': dischargeDetails[0].daySpent,
                'medicineCost': dischargeDetails[0].medicineCost,
                'roomCharge': dischargeDetails[0].roomCharge,
                'doctorFee': dischargeDetails[0].doctorFee,
                'OtherCharge': dischargeDetails[0].OtherCharge,
                'total': dischargeDetails[0].total,
            }
        else:
            patientDict = {
                'is_discharged': False,
                'patient': patient,
                'patientId': request.user.id,
            }
        return render(request, 'hospital/patient_discharge.html', context=patientDict)
    except Exception as e:
        logger.error(f"Error loading discharge info for patient {request.user.username}: {e}")
        return redirect('patient-dashboard')


#About & Contact 
def aboutus_view(request):
    return render(request, 'hospital/aboutus.html')


def contactus_view(request):
    sub = forms.ContactusForm()
    if request.method == 'POST':
        sub = forms.ContactusForm(request.POST)
        if sub.is_valid():
            # IMPROVED: send_mail was unhandled — any SMTP error caused a 500 crash
            try:
                email = sub.cleaned_data['Email']
                name = sub.cleaned_data['Name']
                message = sub.cleaned_data['Message']
                send_mail(
                    str(name) + ' || ' + str(email),
                    message,
                    settings.EMAIL_HOST_USER,
                    settings.EMAIL_RECEIVING_USER,
                    fail_silently=False
                )
                logger.info(f"Contact form submitted by {name} ({email})")
                return render(request, 'hospital/contactussuccess.html')
            except Exception as e:
                logger.error(f"Failed to send contact email: {e}")
                return render(request, 'hospital/contactus.html', {
                    'form': sub,
                    'error': 'Please check your internet connection and try again. If the problem continues, contact us.'
                })
    return render(request, 'hospital/contactus.html', {'form': sub})