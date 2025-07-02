# coding: utf-8

from __future__ import absolute_import

from flask import json
from six import BytesIO

from swagger_server.models.auth_user import AuthUser  # noqa: E501
from swagger_server.models.error_response import ErrorResponse  # noqa: E501
from swagger_server.models.login_request import LoginRequest  # noqa: E501
from swagger_server.models.signup_request import SignupRequest  # noqa: E501
from swagger_server.test import BaseTestCase


class TestAuthController(BaseTestCase):
    """AuthController integration test stubs"""

    def test_auth_check_get(self):
        """Test case for auth_check_get

        Check authentication status
        """
        response = self.client.open(
            '/auth/check',
            method='GET')
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))

    def test_auth_login_post(self):
        """Test case for auth_login_post

        Log in existing user
        """
        body = LoginRequest()
        response = self.client.open(
            '/auth/login',
            method='POST',
            data=json.dumps(body),
            content_type='application/json')
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))

    def test_auth_logout_post(self):
        """Test case for auth_logout_post

        Log out current user
        """
        response = self.client.open(
            '/auth/logout',
            method='POST')
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))

    def test_auth_signup_post(self):
        """Test case for auth_signup_post

        Sign up a new user
        """
        body = SignupRequest()
        response = self.client.open(
            '/auth/signup',
            method='POST',
            data=json.dumps(body),
            content_type='application/json')
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))


if __name__ == '__main__':
    import unittest
    unittest.main()
