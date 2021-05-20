/* tslint:disable */
/* eslint-disable */
/**
 * RMF API Server
 * No description provided (generated by Swagger Codegen https://github.com/swagger-api/swagger-codegen)
 *
 * OpenAPI spec version: 0.1.0
 *
 *
 * NOTE: This class is auto generated by the swagger code generator program.
 * https://github.com/swagger-api/swagger-codegen.git
 * Do not edit the class manually.
 */
/**
 *
 * @export
 * @interface LiftState
 */
export interface LiftState {
  /**
   *
   * @type {Time}
   * @memberof LiftState
   */
  lift_time?: any;
  /**
   *
   * @type {string}
   * @memberof LiftState
   */
  lift_name?: any;
  /**
   *
   * @type {Array&lt;string&gt;}
   * @memberof LiftState
   */
  available_floors?: any;
  /**
   *
   * @type {string}
   * @memberof LiftState
   */
  current_floor?: any;
  /**
   *
   * @type {string}
   * @memberof LiftState
   */
  destination_floor?: any;
  /**
   *
   * @type {number}
   * @memberof LiftState
   */
  door_state?: any;
  /**
   *
   * @type {number}
   * @memberof LiftState
   */
  motion_state?: any;
  /**
   *
   * @type {Array&lt;number&gt;}
   * @memberof LiftState
   */
  available_modes: any;
  /**
   *
   * @type {number}
   * @memberof LiftState
   */
  current_mode?: any;
  /**
   *
   * @type {string}
   * @memberof LiftState
   */
  session_id?: any;
}