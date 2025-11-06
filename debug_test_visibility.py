"""
Debug script to identify why users aren't seeing tests after being added to cohorts.
This script checks all the relationships and filters needed for test visibility.
"""

def debug_user_test_visibility(user):
    """
    Debug helper to check why a user may or may not see tests
    Args:
        user: Django User instance
    """
    from assessment.models import Test, Cohort, CohortMembership, TestCategory
    
    print(f"\n{'='*60}")
    print(f"DEBUGGING TEST VISIBILITY FOR USER: {user.username}")
    print(f"{'='*60}\n")
    
    # Step 1: Check if user is in any cohorts
    user_cohorts = CohortMembership.objects.filter(user=user).select_related('cohort')
    print(f"1. USER COHORT MEMBERSHIPS:")
    if not user_cohorts.exists():
        print("   ❌ User is NOT in any cohorts!")
        print("   → Add user to a cohort in the admin panel\n")
        return
    
    for membership in user_cohorts:
        cohort = membership.cohort
        print(f"   ✓ Cohort: {cohort.name}")
        print(f"     - Active: {cohort.is_active}")
        print(f"     - Start Date: {cohort.start_date}")
        print(f"     - End Date: {cohort.end_date or 'No end date'}")
        print(f"     - Joined: {membership.joined_at}")
    
    print()
    
    # Step 2: Check enabled categories for user's cohorts
    print(f"2. ENABLED TEST CATEGORIES IN USER'S COHORTS:")
    enabled_categories = TestCategory.objects.filter(
        cohorts__members__user=user
    ).distinct()
    
    if not enabled_categories.exists():
        print("   ❌ No test categories are enabled for user's cohorts!")
        print("   → Go to cohort admin and assign test categories\n")
        return
    
    for category in enabled_categories:
        cohorts_with_cat = Cohort.objects.filter(
            members__user=user,
            enabled_categories=category
        ).values_list('name', 'is_active')
        
        print(f"   ✓ {category.name} (Stage {category.stage_number})")
        print(f"     - Category Active: {category.is_active}")
        for cohort_name, cohort_active in cohorts_with_cat:
            print(f"     - In Cohort: {cohort_name} (Active: {cohort_active})")
    
    print()
    
    # Step 3: Check tests in those categories
    print(f"3. TESTS IN ENABLED CATEGORIES:")
    tests_in_categories = Test.objects.filter(
        category__in=enabled_categories
    )
    
    if not tests_in_categories.exists():
        print("   ❌ No tests exist in the enabled categories!")
        print("   → Create tests for the enabled categories\n")
        return
    
    for test in tests_in_categories:
        print(f"   • {test.title}")
        print(f"     - Category: {test.category.name}")
        print(f"     - Test Active: {test.is_active}")
        print(f"     - Category Active: {test.category.is_active}")
        
        # Check if test's category is in active cohorts
        cohorts_with_test_cat = Cohort.objects.filter(
            members__user=user,
            enabled_categories=test.category
        )
        
        if cohorts_with_test_cat.exists():
            print(f"     - ✓ Category enabled in user's cohort(s):")
            for cohort in cohorts_with_test_cat:
                print(f"       • {cohort.name} (Active: {cohort.is_active})")
        else:
            print(f"     - ❌ Category NOT enabled in user's cohorts")
    
    print()
    
    # Step 4: Run the CURRENT dashboard query
    print(f"4. CURRENT DASHBOARD QUERY RESULTS:")
    current_query = Test.objects.filter(
        is_active=True,
        category__cohorts__members__user=user
    ).distinct()
    
    print(f"   Tests returned by current query: {current_query.count()}")
    for test in current_query:
        print(f"   ✓ {test.title}")
    
    if not current_query.exists():
        print("   ❌ Current query returns NO tests!")
    
    print()
    
    # Step 5: Run the FIXED dashboard query
    print(f"5. RECOMMENDED FIXED QUERY RESULTS:")
    fixed_query = Test.objects.filter(
        is_active=True,
        category__is_active=True,
        category__cohorts__is_active=True,
        category__cohorts__members__user=user
    ).distinct()
    
    print(f"   Tests returned by fixed query: {fixed_query.count()}")
    for test in fixed_query:
        print(f"   ✓ {test.title}")
    
    if not fixed_query.exists():
        print("   ❌ Fixed query STILL returns no tests!")
        print("   → Check that:")
        print("      1. User is in an ACTIVE cohort")
        print("      2. Cohort has ACTIVE test categories enabled")
        print("      3. Those categories have ACTIVE tests")
    
    print()
    
    # Step 6: Check for common issues
    print(f"6. COMMON ISSUES CHECK:")
    
    # Issue 1: Inactive cohorts
    inactive_cohorts = Cohort.objects.filter(
        members__user=user,
        is_active=False
    )
    if inactive_cohorts.exists():
        print(f"   ⚠️  User is in {inactive_cohorts.count()} INACTIVE cohort(s):")
        for cohort in inactive_cohorts:
            print(f"      • {cohort.name}")
    
    # Issue 2: Inactive categories
    inactive_categories = TestCategory.objects.filter(
        cohorts__members__user=user,
        is_active=False
    ).distinct()
    if inactive_categories.exists():
        print(f"   ⚠️  User's cohorts have {inactive_categories.count()} INACTIVE categories:")
        for cat in inactive_categories:
            print(f"      • {cat.name}")
    
    # Issue 3: Inactive tests
    inactive_tests = Test.objects.filter(
        category__cohorts__members__user=user,
        is_active=False
    ).distinct()
    if inactive_tests.exists():
        print(f"   ⚠️  {inactive_tests.count()} INACTIVE tests in user's cohort categories:")
        for test in inactive_tests:
            print(f"      • {test.title}")
    
    print(f"\n{'='*60}\n")


# Django shell usage instructions
if __name__ == "__main__":
    print("""
    This is a debugging script. To use it in Django shell:
    
    1. Run: python manage.py shell
    
    2. Then execute:
       from django.contrib.auth.models import User
       exec(open('debug_test_visibility.py').read())
       
       # Replace 'username' with actual username
       user = User.objects.get(username='testuser')
       debug_user_test_visibility(user)
    
    3. Review the output to identify the issue
    """)
    
    