import flask
import httplib2
import os
from application import app
from oauth2client import client
from logging import info as linfo
import atom.data
import gdata.gauth
import gdata.data
import gdata.contacts.client
import gdata.contacts.data

client_info = {
    "client_id": os.environ['CONTACTS_CLIENT_ID'],
    "client_secret": os.environ['CONTACTS_CLIENT_SECRET'],
    "redirect_uris": [],
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    "token_uri": "https://accounts.google.com/o/oauth2/token"
}

scopes = 'https://www.google.com/m8/feeds/'

CONTACT_XML = '''
<atom:entry xmlns:atom="http://www.w3.org/2005/Atom"
    xmlns:gd="http://schemas.google.com/g/2005">
  <atom:category scheme="http://schemas.google.com/g/2005#kind"
    term="http://schemas.google.com/contact/2008#contact"/>
  <gd:name>
     <gd:fullName>{name}</gd:fullName>
  </gd:name>
  <gd:email rel="http://schemas.google.com/g/2005#work"
    primary="true"
    address="{email}" displayName="{name}"/>
  <gd:phoneNumber rel="http://schemas.google.com/g/2005#mobile"
    primary="true">{mobile}</gd:phoneNumber>
</atom:entry>
'''


def create_contact(gd_client):
    new_contact = gdata.contacts.data.ContactEntry()
    # Set the contact's name.
    new_contact.name = gdata.data.Name(
        given_name=gdata.data.GivenName(text='Elizabeth'),
        family_name=gdata.data.FamilyName(text='Bennet'),
        full_name=gdata.data.FullName(text='Elizabeth Bennet'))
    new_contact.content = atom.data.Content(text='Notes')
    # Set the contact's email addresses.
    new_contact.email.append(gdata.data.Email(address='liz@gmail.com',
                                              primary='true',
                                              rel=gdata.data.WORK_REL,
                                              display_name='E. Bennet'))
    new_contact.email.append(gdata.data.Email(address='liz@example.com',
                                              rel=gdata.data.HOME_REL))
    # Set the contact's phone numbers.
    new_contact.phone_number.append(gdata.data.PhoneNumber(text='(206)555-1212',
                                                           rel=gdata.data.WORK_REL,
                                                           primary='true'))
    new_contact.phone_number.append(gdata.data.PhoneNumber(text='(206)555-1213',
                                                           rel=gdata.data.HOME_REL))
    # Set the contact's IM address.
    new_contact.im.append(gdata.data.Im(address='liz@gmail.com',
                                        primary='true', rel=gdata.data.HOME_REL,
                                        protocol=gdata.data.GOOGLE_TALK_PROTOCOL))
    # Set the contact's postal address.
    new_contact.structured_postal_address.append(gdata.data.StructuredPostalAddress(
        rel=gdata.data.WORK_REL, primary='true',
        street=gdata.data.Street(text='1600 Amphitheatre Pkwy'),
        city=gdata.data.City(text='Mountain View'),
        region=gdata.data.Region(text='CA'),
        postcode=gdata.data.Postcode(text='94043'),
        country=gdata.data.Country(text='United States')))
    # Send the contact data to the server.
    contact_entry = gd_client.CreateContact(new_contact)
    linfo('Contact\'s ID: %s' % contact_entry.id.text)
    return contact_entry


@app.route('/oauth')
def index():
    if 'credentials' not in flask.session:
        return flask.redirect(flask.url_for('oauth2callback'))

    credentials = client.OAuth2Credentials.from_json(
        flask.session['credentials'])

    if credentials.access_token_expired:
        return flask.redirect(flask.url_for('oauth2callback'))
    else:
        linfo('Valid credentials, using contacts api')
        http_auth = credentials.authorize(httplib2.Http())
        url = 'https://www.google.com/m8/feeds/contacts/default/full'
        headers = {'GData-Version': '3.0',
                   'Content-Type': 'application/atom+xml'}

        body = CONTACT_XML.format(name='Test Contact',
                                  email='test@email.com',
                                  mobile='(11) 111-222-333')

        linfo('Listing contacts...')
        status1, content1 = http_auth.request(url, headers=headers)
        linfo('Creating contact...')
        status2, content2 = http_auth.request(url,
                                              method='POST',
                                              headers=headers,
                                              body=body)
        linfo('Listing contacts again...')
        status3, content3 = http_auth.request(url, headers=headers)

        return '%s\n\n\n\n%s\n\n\n\n%s' % (str(content1),
                                           str(content2),
                                           str(content3))


@app.route('/oauth/oauth2callback')
def oauth2callback():
    flow = client.OAuth2WebServerFlow(
            client_info['client_id'],
            client_info['client_secret'],
            scopes,
            user_agent=None,
            auth_uri=client_info['auth_uri'],
            token_uri=client_info['token_uri']
    )

    if 'error' in flask.request.args:
        return str(flask.request.args)
    elif 'code' not in flask.request.args:
        auth_uri = flow.step1_get_authorize_url(
            redirect_uri=flask.url_for('oauth2callback', _external=True)
        )
        return flask.redirect(auth_uri)
    else:
        auth_code = flask.request.args.get('code')
        flow.redirect_uri = flask.url_for('oauth2callback', _external=True)
        credentials = flow.step2_exchange(auth_code)
        flask.session['credentials'] = credentials.to_json()
        return flask.redirect(flask.url_for('index'))


@app.route('/gdata/oauth')
def gdata_oauth():
    request_token = gdata.gauth.OAuth2Token(
        client_id=client_info['client_id'],
        client_secret=client_info['client_secret'],
        scope=scopes,
        user_agent=None)

    return flask.redirect(
        request_token.generate_authorize_url(
            redirect_uri=flask.url_for('gdata_oauth2callback', _external=True)))


@app.route('/gdata/oauth2callback')
def gdata_oauth2callback():
    if 'error' in flask.request.args:
        return str(flask.request.args.get('error'))
    elif 'code' not in flask.request.args:
        return flask.redirect(flask.url_for('gdata_oauth'))
    else:
        request_token = gdata.gauth.OAuth2Token(
            client_id=client_info['client_id'],
            client_secret=client_info['client_secret'],
            scope=scopes,
            user_agent=None)
        request_token.redirect_uri =\
            flask.url_for('gdata_oauth2callback', _external=True)
        request_token.get_access_token(flask.request.args.get('code'))
        gd_client = gdata.contacts.client.ContactsClient(
            source='your-project-id',
            auth_token=request_token)
        contact = create_contact(gd_client)
        flask.session['contact'] = str(contact)
        return flask.redirect(flask.url_for('gdata_oauth_result'))


@app.route('/gdata/result')
def gdata_oauth_result():
    if 'contact' in flask.session:
        return flask.session['contact']

    return flask.redirect('gdata_oauth')
