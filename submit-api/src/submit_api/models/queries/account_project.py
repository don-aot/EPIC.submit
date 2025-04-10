# Copyright © 2024 Province of British Columbia
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Model to handle all complex operations related to User."""

import time
from sqlalchemy import or_

from submit_api.enums.role import RoleEnum
from submit_api.models import AccountProject, Project, db, User
from submit_api.models.account_project_search_options import AccountProjectSearchOptions
from submit_api.models.package import Package
from submit_api.models.user import UserType
from submit_api.utils.token_info import TokenInfo


# pylint: disable=too-few-public-methods


class ProjectQueries:
    """Query module for complex projects queries"""

    @classmethod
    def get_projects_by_proponent_id(cls, proponent_id: int):
        """Find projects by proponent_id"""
        query = db.session.query(Project).filter(
            Project.proponent_id == proponent_id
        )
        return query.all()

    @classmethod
    def get_account_project_by_id(cls, account_project_id: int):
        """Find account project by id."""
        query = db.session.query(AccountProject).filter(
            AccountProject.id == account_project_id
        )

        package_query = cls._filter_packages_by_user_access()
        if package_query:
            filtered_package_ids = package_query.with_entities(Package.id).subquery().select()
            query = query.join(Package).filter(
                Package.id.in_(filtered_package_ids)).options(
                db.contains_eager(AccountProject.packages))
        return query.first()

    @classmethod
    def get_filtered_account_projects(cls, account_id: int = None, search_options: AccountProjectSearchOptions = None):
        """Find projects by account_id with optional search and pagination."""
        start_time = time.time()
        query = db.session.query(AccountProject)
        query_time = time.time()
        print(f"Query initialization took {query_time - start_time:.4f} seconds")

        # Apply account_id filter only if provided
        if account_id is not None:
            query = query.filter(AccountProject.account_id == account_id)
        account_id_filter_time = time.time()
        print(f"Account ID filter took {account_id_filter_time - query_time:.4f} seconds")

        package_query = None
        # Apply search filters if provided
        if search_options and any(bool(search_option) for search_option in search_options.__dict__.values()):
            package_query = cls._filter_by_search_criteria(search_options)
        search_filter_time = time.time()
        print(f"Search filter application took {search_filter_time - account_id_filter_time:.4f} seconds")

        package_query = cls._filter_packages_by_user_access(package_query)
        user_access_filter_time = time.time()
        print(f"User access filter took {user_access_filter_time - search_filter_time:.4f} seconds")

        if package_query:
            filtered_package_ids = package_query.with_entities(Package.id).subquery().select()
            query = query.join(Package).filter(
                Package.id.in_(filtered_package_ids)).options(
                db.contains_eager(AccountProject.packages))
        package_query_time = time.time()
        print(f"Package query processing took {package_query_time - user_access_filter_time:.4f} seconds")

        result = query.all()
        end_time = time.time()
        print(f"Query execution and result fetching took {end_time - package_query_time:.4f} seconds")
        print(f"Total execution time: {end_time - start_time:.4f} seconds")
        return result

    @classmethod
    def _filter_by_search_criteria(cls, search_options: AccountProjectSearchOptions):
        """Apply various filters based on search options."""
        # Subquery to get packages based on search criteria
        package_query = db.session.query(Package)

        if search_options.search_text:
            package_query = cls._filter_by_search_text(package_query, search_options.search_text)
        if search_options.status:
            package_query = cls._filter_by_submission_status(package_query, search_options.status)
        if search_options.submitted_on_start or search_options.submitted_on_end:
            package_query = cls._filter_by_submission_dates(
                package_query, search_options.submitted_on_start, search_options.submitted_on_end
            )

        return package_query

    @classmethod
    def _filter_packages_by_user_access(cls, package_query=None):
        """Filter packages by user access."""
        auth_guid = TokenInfo.get_id()
        user = User.get_by_guid(auth_guid)

        if not user:
            raise ValueError("User not found.")

        if user.type == UserType.STAFF:
            return package_query

        if not user.account_user:
            raise ValueError("User account not found.")

        user_role = user.account_user.role
        role_name = user_role.role.role_name
        if role_name in [RoleEnum.SUBMISSION_ADMIN.value, RoleEnum.PROJECT_ADMIN.value]:
            return package_query

        if not package_query:
            package_query = db.session.query(Package)

        package_ids = user_role.package_ids
        if not package_ids:
            return package_query.filter(False)

        return package_query.filter(Package.id.in_(package_ids))

    @classmethod
    def _filter_by_search_text(cls, query, search_text):
        """Filter by search text across package name."""
        return query.filter(
            or_(
                Package.name.ilike(f"%{search_text}%"),
                Project.name.ilike(f"%{search_text}%")
            )
        )

    @classmethod
    def _filter_by_submission_status(cls, query, statuses):
        """Filter by submission status using overlap."""
        status_values = [status.value for status in statuses]

        # check if Package.status has all the values in status_values
        return query.filter(Package.status.op("@>")(status_values))

    @classmethod
    def _filter_by_submission_dates(cls, query, submitted_on_start, submitted_on_end):
        """Filter by the submitted_on date range."""
        if submitted_on_start:
            query = query.filter(Package.submitted_on >= submitted_on_start)
        if submitted_on_end:
            query = query.filter(Package.submitted_on <= submitted_on_end)
        return query
