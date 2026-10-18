(define (domain blocksworld)
  (:requirements :strips)
  (:predicates (clear ?x)
               (on-table ?x)
               (arm-empty)
               (holding ?x)
               (on ?x ?y))

  (:action pick-up
    :parameters (?x)
    :precondition (and (clear ?x) (on-table ?x) (arm-empty))
    :effect (and (holding ?x)
                 (not (clear ?x))
                 (not (on-table ?x))
                 (not (arm-empty))))

  (:action put-down
    :parameters (?x)
    :precondition (holding ?x)
    :effect (and (clear ?x)
                 (arm-empty)
                 (on-table ?x)
                 (not (holding ?x))))

  (:action stack
    :parameters (?x ?y)
    :precondition (and (holding ?x) (clear ?y))
    :effect (and (clear ?x)
                 (arm-empty)
                 (on ?x ?y)
                 (not (holding ?x))
                 (not (clear ?y))))

  (:action unstack
    :parameters (?x ?y)
    :precondition (and (on ?x ?y) (clear ?x) (arm-empty))
    :effect (and (holding ?x)
                 (clear ?y)
                 (not (clear ?x))
                 (not (on ?x ?y))
                 (not (arm-empty)))))
