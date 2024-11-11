=============
 Messenger
=============

.. contents::
   :local:

Installation
============

* Make configuration required for `queue_job <https://github.com/OCA/queue/tree/16.0/queue_job#id4>`__ module. In particular:

  * add ``queue_job`` to `server wide modules <https://odoo-development.readthedocs.io/en/latest/admin/server_wide_modules.html>`__, e.g.::

        --load base,web,queue_job

* `Install <https://odoo-development.readthedocs.io/en/latest/odoo/usage/install-module.html>`__ this module in a usual way

* If your Messengers use webhooks (most likely), be sure that url opens correct database without asking to select one


User Access Levels
==================

* ``User``: read-only ``All Messeges``
* ``Developer``: same as User, but read-only ``Messengers``, ``Jobs``
* ``Administrator``: same as Developer, but with access to **Secrets**

Project
=======

* Open menu ``[[ Messengers ]] >> Messengers``
* Create a project

  * **Name**, e.g. *OdooTelegramBot*

  * In the ``Parameters`` tab

    * **Params**
      * **Key**
      * **Value**

  * In the ``Advanced`` tab

    * **Common_code**: code that is executed before running any
      project's task. Can be used for initialization or for helpers. Any variables
      and functions that don't start with underscore symbol will be available in
      task's code.
    * **Available Tasks**. In the ``Available Tasks`` tab

      **Name**, e.g. *Setup*.
      **Code**: code with at least one of the following functions

      * ``handle_cron()``
      * ``handle_db(records)``

        * ``records``: all records on which this task is triggered

      * ``handle_webhook(httprequest)``

        * ``httprequest``: contains information about request, e.g.

          * `httprequest.data <https://werkzeug.palletsprojects.com/en/1.0.x/wrappers/#werkzeug.wrappers.BaseRequest.data>`__: request data
          * `httprequest.files <https://werkzeug.palletsprojects.com/en/1.0.x/wrappers/#werkzeug.wrappers.BaseRequest.files>`__: uploaded files
          * `httprequest.remote_addr <https://werkzeug.palletsprojects.com/en/1.0.x/wrappers/#werkzeug.wrappers.BaseRequest.remote_addr>`__: ip address of the caller.
          * see `Werkzeug doc
            <https://werkzeug.palletsprojects.com/en/1.0.x/wrappers/#werkzeug.wrappers.BaseRequest>`__
            for more information.
        * optionally can return data as a response to the webhook request; any data transferred in this way are logged via ``log_transmission`` function:

          * for *json* webhook:
            * ``return json_data``
          * for *x-www-form-urlencoded* webhook:
            * ``return data_str``
            * ``return data_str, status``
            * ``return data_str, status, headers``

              * ``status`` is a response code, e.g. ``200``, ``403``, etc.
              * ``headers`` is a list of key-value tuples, e.g. ``[('Content-Type', 'text/html')]``
      * ``handle_button()``

    * **Cron Triggers**, **DB Triggers**, **Webhook Triggers**, **Manual
      Triggers**: when to execute the Code. See below for further information


Job Triggers
============

Cron
----

* **Trigger Name**, e.g. ``NIGHTLY_TRIGGER``
* **Execute Every**: every 2 hours, every 1 week, etc.
* **Next Execution Date**
* **Scheduler User**

DB
--

* **Trigger Name**, e.g. ``PRODUCT_PRICE_CHANGE``
* **Model**
* **Trigger Condition**

  * On Creation
  * On Update
  * On Creation & Update
  * On Deletion
  * Based on Timed Condition

    * Allows to trigger task before, after on in time of Date/Time fields, e.g.
      1 day after Sale Order is closed

* **Apply on**: records filter
* **Before Update Domain**: additional records filter for *On Update* event
* **Watched fields**: fields list for *On Update* event

Webhook
-------

* **Trigger Name**, e.g. ``ON_EXTERNAL_UPDATE``
* **Webhook Type**: *application/x-www-form-urlencoded* or *application/json*

* **Webhook URL**: readonly.

Button
------

* **Trigger Name**, e.g. ``SETUP``

Code
====

Available variables and functions:
----------------------------------

Base
~~~~

* ``env``: Odoo Environment
* ``log(message, level=LOG_INFO)``: logging function to record debug information

  log levels:

  * ``LOG_DEBUG``
  * ``LOG_INFO``
  * ``LOG_WARNING``
  * ``LOG_ERROR``
  *

* ``log_transmission(recipient_str, data_str)``: report on data transfer to external recipients

Links
~~~~~

* ``<record>.set_link(relation_name, external, sync_date=None, allow_many2many=False) -> link``: makes link between Odoo and external resource

  * ``allow_many2many``: when False raises an error if there is a link for the
    ``record`` and ``relation_name`` or if there is a link for ``relation_name``
    and ``external``;

* ``<records>.search_links(relation_name) -> links``
* ``get_link(relation_name, external_ref, model=None) -> link``

Odoo Link usage:

* ``link.odoo``: normal Odoo record

  * ``link.odoo._name``: model name, e.g. ``res.partner``
  * ``link.odoo.id``: odoo record id
  * ``link.odoo.<field>``: some field of the record, e.g. ``link.odoo.email``: partner email

* ``link.external``: external reference, e.g. external id of a partner
* ``link.sync_date``: last saved date-time information
* ``links.odoo``: normal Odoo RecordSet
* ``links.external``: list of all external references
* ``links.sync_date``: minimal data-time among links
* ``links.update_links(sync_date=None)``: set new sync_date value; if value is not passed, then ``now()`` is used
* ``links.unlink()``: delete links
* ``for link in links:``: iterate over links
* ``if links``: check that link set is not empty
* ``len(links)``: number of links in the set


Project Values
~~~~~~~~~~~~~~

* ``params.<PARAM_NAME>``: project params
* ``webhooks.<WEBHOOK_NAME>``: contains webhook url; only in tasks' code

Event
~~~~~

* ``trigger_name``: available in tasks' code only
* ``user``: user related to the event, e.g. who clicked a button

Asynchronous work
~~~~~~~~~~~~~~~~~

* ``add_job(func_name, **options)(*func_args, **func_kwargs)``: call a function asynchronously; options are similar to ``with_delay`` method of ``queue_job`` module:

  * ``priority``: Priority of the job, 0 being the higher priority. Default is 10.
  * ``eta``: Estimated Time of Arrival of the job. It will not be executed before this date/time.
  * ``max_retries``: maximum number of retries before giving up and set the job
    state to 'failed'. A value of 0 means infinite retries. Default is 5.
  * ``description`` human description of the job. If None, description is
    computed from the function doc or name
  * ``identity_key`` key uniquely identifying the job, if specified and a job
    with the same key has not yet been run, the new job will not be added.


Attachments
~~~~~~~~~~~

* ``attachment._public_url()``:  generates access url. Can be used to pass attachments to an external system as url, instead of direct uploading the content.

Libs
~~~~

* ``json``
* ``time``
* ``datetime``
* ``dateutil``
* ``timezone``
* ``b64encode``
* ``b64decode``

Tools
~~~~~

* ``url2base64``
* ``url2bin``
* ``get_lang(env, lang_code=False)``: returns `res.lang` record
* ``html2plaintext``
* ``type2str``: get type of the given object
* ``DEFAULT_SERVER_DATETIME_FORMAT``

Exceptions
~~~~~~~~~~

* ``UserError``
* ``ValidationError``
* ``RetryableJobError``: raise to restart job from beginning; e.g. in case of temporary errors like broken connection
* ``OSError``

Running Job
===========

Depending on Trigger, a job may:

* be added to a queue or runs immediatly
* be retried in case of failure

  * if ``RetryableJobError`` is raised, then job is retried automatically in following scheme:

    * After first failure wait 5 minute
    * If it's not succeeded again, then wait another 15 minutes
    * If it's not succeeded again, then wait another 60 minutes
    * If it's not succeeded again, then wait another 3 hours
    * Try again for the fifth time and stop retrying if it's still failing

Cron
----

* job is added to the queue before run
* failed job can be retried if failed

DB
--

* job is added to the queue before run
* failed job can be retried if failed

Webhook
-------

* runs immediately
* failed job cannot be retried via backend UI; the webhook should be called again.

Button
------

* runs immediately
* to retry click the button again

Execution Logs
==============

In Project, Task and Job Trigger forms you can find ``Logs`` button in top-right
hand corner. You can filter and group logs by following fields:

* Messenger
* Task
* Job Trigger
* Job Start Time
* Log Level
* Status (Success / Fail)