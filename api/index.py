from onlinexam.wsgi import application

# Vercel Python entrypoint for the Django app. All routes are rewritten here
# so Django and WhiteNoise handle both page and static asset requests.
app = application
