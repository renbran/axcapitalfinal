# Changelog

## 17.0.1.0.1

Implement `formio.form` model method `_component_selectboxes_data_url_values_labels`.
It generates a similar datastructure like the formio-data (library) `selectboxesCompopnent` getter `values_labels` does, with the default Values as Data Source Type.
However this method generates `selectboxesComponent` property `values_labels`, when the Data Source Type is URL and the URL is relative (this Odoo instance).

## 17.0.1.0

Initial release.
