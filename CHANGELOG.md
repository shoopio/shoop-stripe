# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

Enter here all the changes made to the development version

### [2.0.0] - 2020-08-06

## Added

- Add support for Shuup 2 and drop support for older versions

For patching old releases use "shuup1" branch.

## [1.0.5] - 2020-05-22

### Changed

- Make key fields longer

## [1.0.4] - 2020-05-27

- Admin: Fix payment link URL for notify event

## [1.0.3] - 2020-05-27

- Admin: Fix bug in email information

## [1.0.2] - 2020-05-27

- Admin: Add information about the email where payment link is sent to at
  order section.

## [1.0.1] - 2020-05-27

- Add option to send payment link from order admin. Sending payment link is
  triggered through notify event. Payment link is shown in special view with
  order details.
